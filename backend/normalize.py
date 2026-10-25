from prompts import get_review_prompt
from pydantic import BaseModel
from langchain.chat_models import init_chat_model
from sentence_transformers import SentenceTransformer
import numpy as np
from database import get_known_techs, add_techs, add_aliases, PaperSummary

'''

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

terms = ["LLM", "large language model", "CNN", "RAG", "Retrieval Augemented Generation"]

embeddings = model.encode(terms)
similarities = model.similarity(embeddings, embeddings)

print(similarities)'''


import re          # needed for get_numbers() below
import numpy as np
 

def normalize(papers):
    """Normalize the technologies in the papers"""
 
    THRESHOLD = 0.7

    def is_acronym(short, long):
        """True if `short` is an acronym/abbreviation of the phrase `long`.
        "rag" <- "retrieval-augmented generation", "adam" <- "adaptive moment estimation"
        Each chunk of `short` must be the START of the next word of `long`."""
        
        STOP = {"from", "of", "for", "and", "the", "in", "on", "with", "to"}
        
        short = short.lower()
        if not short.isalpha() or len(short) < 2:   # single token, letters only
            return False
        words = [w for w in re.split(r"[\s\-]+", long.lower()) if w]
        if len(words) < 2:                          # a one-word "long form" is not an expansion
            return False

        def match(s, w, used):
            # s = letters of the acronym still to place, w = words still available
            if not s:
                return used >= 2                    # must have spanned at least 2 words
            if not w:
                return False
            word = w[0]
            # try giving this word the longest chunk first, then shorter ones
            for k in range(min(len(s), len(word)), 0, -1):
                if word.startswith(s[:k]) and match(s[k:], w[1:], used + 1):
                    return True
            # a small word like "from" may be skipped, but never the first word
            if used > 0 and word in STOP:
                return match(s, w[1:], used)
            return False


        # trailing "s" has no word of its own to start. If the check fails, retry without it.
        if match(short, words, 0):
            return True
        return short.endswith("s") and len(short) > 2 and match(short[:-1], words, 0)
 
    def split_parenthetical(tech):
                """ "linear programming (lp)" -> ["linear programming", "lp"].
                Only splits when one side is an acronym of the other, so "stable diffusion (v1.5)"
                stays whole and its version number isn't thrown away."""
                m = re.fullmatch(r"(.+?)\s*\((.+?)\)", tech)
                if m:
                    outside, inside = m.group(1).strip(), m.group(2).strip()
                    if is_acronym(inside, outside) or is_acronym(outside, inside):
                        return [outside, inside]
                return [tech]


    def get_ngrams(text, n=3):
        text = text.lower().replace("-", " ").replace(" ", "")
        return {text[i:i+n] for i in range(len(text) - n + 1)}
 
 
    def ngram_similarity(a, b, n=3):
        a_ngrams = get_ngrams(a, n)
        b_ngrams = get_ngrams(b, n)
 
        if not a_ngrams or not b_ngrams:
            return 1.0 if a.lower() == b.lower() else 0.0
 
        return len(a_ngrams & b_ngrams) / len(a_ngrams | b_ngrams)
 
 
    def get_numbers(text):
        # "gpt-3" -> {"3"}, "llama 2 70b" -> {"2", "70"}, "stable diffusion 1.5" -> {"1.5"}
        return set(re.findall(r"\d+(?:\.\d+)?", text))
 
 
    def eval(candidate: str, vector: list[float], matrix :list[list[float]], known_keywords: list[dict]):
        """Helper Function to decide the action on each word.
 
        Returns (decision, tech_name):
          "merge"     -> candidate is EXACTLY a known name/alias (nothing new to save)
          "new_alias" -> candidate is a NEW spelling of a known tech (save it as an alias)
          "review"    -> unsure; tech_name is the closest known tech, for the reviewer
          "new"       -> a technology we have never seen
        """
        # First run ever
        if len(known_keywords) == 0:
            return "new", None
 
        # For every known tech: does it contain the same numbers as the candidate?
        candidate_numbers = get_numbers(candidate)
        numbers_match = [get_numbers(known["name"]) == candidate_numbers for known in known_keywords]
 
        max_ngram = (0.0, None)
 
        for i, known in enumerate(known_keywords):
            
            if candidate == known["name"] or candidate in (known["aliases"] or []):
                return "merge", known["name"]
 
            # Skip n-gram matching against techs that have different numbers.
            if not numbers_match[i]:
                continue

            # Acronym check (checks both directions, against the name and its aliases)
            for name in [known["name"]] + (known["aliases"] or []):
                if is_acronym(candidate, name) or is_acronym(name, candidate):
                    return "new_alias", known["name"]
 
            # Track best N gram candidate
            temp = ngram_similarity(known["name"], candidate)
            if temp > max_ngram[0]:
                max_ngram = (temp, i)
 
        # Check for max_ngram matching
        if max_ngram[0] > THRESHOLD:
            return "new_alias", known_keywords[max_ngram[1]]["name"]
 
        # Check for embedding
        # (Dot product == cosine similarity only because all vectors are normalized.)
        sim_scores = matrix @ vector
 
        # Number guard, applied by MASKING any tech with different numbers never wins
        for i, ok in enumerate(numbers_match):
            if not ok:
                sim_scores[i] = -1.0
 
        # Get best scores
        max_indices = np.argsort(sim_scores)[-2:][::-1]
        max_vals = sim_scores[max_indices]
 
        # Avoid crashing if max_vals is only 1 elem
        second_best = max_vals[1] if len(max_vals) > 1 else 0.0
 
        if max_vals[0] >= 0.6:
            # If second max is not smth the algo rooted out with -1
            if second_best >= 0.6:
                return "review", (known_keywords[max_indices[0]]['name'], known_keywords[max_indices[1]]['name'])
            return "review", (known_keywords[max_indices[0]]['name'],)
        else:
            return "new", None
 
    print("Starting Normalizing")
 
    # Get known info
    known_techs, matrix = get_known_techs()
    matrix = np.array(matrix, dtype=np.float32)
 
    # Load model
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
 
    # Avoid crashing on first run
    if matrix.size == 0:
        matrix = np.empty((0, 384), dtype=np.float32)
 
    sim_mappings = {}
    new_keywords = []    
    to_review = []      
 
    # Normalize formatting
    keywords = []
    for paper in papers:
        keywords.extend((part, paper.paper_id, paper.summary)
                for tech in paper.technologies
                for part in split_parenthetical(tech.strip().lower()))
 
    # Get Embeddings 
    embeddings = model.encode([k for k, _, _ in keywords], normalize_embeddings=True)
 
    for i, keyword_id in enumerate(keywords):
        embedding = embeddings[i]
        keyword = keyword_id[0]
        p_id = keyword_id[1]
        p_summary = keyword_id[2]

        result, tech_name = eval(keyword, embedding, matrix, known_techs)

        # exact alias was found
        if result == "merge":
            aliases = sim_mappings.get((tech_name, p_id), [])
            aliases.append(keyword)
            sim_mappings[(tech_name, p_id)] = aliases

        # New alias found 
        elif result == "new_alias":
            aliases = sim_mappings.get((tech_name, p_id), [])
            aliases.append(keyword)
            sim_mappings[(tech_name, p_id)] = aliases   
            
            # Add new alias to alias list
            for tech in known_techs:
                if tech["name"] == tech_name:
                    tech["aliases"] = (tech["aliases"] or []) + [keyword]
                    break
        
        # New keyword indetified
        elif result == "new":
            new_tech = {"name": keyword, "embedding": embedding, "aliases": [], "paper_id": p_id }
            known_techs.append(new_tech)
            matrix = np.vstack([matrix, embedding])
            new_keywords.append(new_tech)
            

        # Ambigiuous result to be reviewed by LLM
        else:
            to_review.append({"candidate":keyword, "p_summary": p_summary, 
                              "may_match": tech_name, "paper_id": p_id, "embed": embedding})

    if to_review:
        print("Starting Review........")
        answers, pending, incorrect_matching, groups = review(to_review)
        new_names = {tech["name"] for tech in new_keywords}
        print(to_review)

        for k, group_answer in answers.items():
            print(group_answer)
            for paper in groups[k]:
                if group_answer.final_tech:
                    #print(group_answer.final_tech, paper["may_match"])
                    aliases = sim_mappings.get((group_answer.final_tech, paper["paper_id"]), [])
                    aliases.append(paper["candidate"])
                    sim_mappings[(group_answer.final_tech, paper["paper_id"])] = aliases
            # New technology
                else:
                    if paper["candidate"] not in new_names:
                        new_names.add(paper["candidate"])
                        new_keywords.append({"name": paper["candidate"], "embedding": paper["embed"], "aliases": [], "paper_id": paper["paper_id"] })
                    else:
                        aliases = sim_mappings.get((paper["candidate"], paper["paper_id"]), [])
                        aliases.append(paper["candidate"])
                        sim_mappings[(paper["candidate"], paper["paper_id"])] = aliases
        
        # TO-DO: do smth with pending and incorrect_matching later
    
        return sim_mappings, new_keywords, to_review, pending, incorrect_matching

    return sim_mappings, new_keywords, to_review, None, None
                
class Reviewed(BaseModel):
    choice: int | None 
    id: int
    final_tech: str | None = None 

class ListReviewed(BaseModel):
    reviews: list[Reviewed]


# {"candidate":keyword, "may_match": (tech_name1, tech_name2,), "paper_id": p_id, "p_summary": str }
def review( reviews: list[dict]):
    "Final output should just be added to sim_mappings or new_keywords"

    def collapse_reviews(reviews: list[dict]):
        """Returns list of only unique candidate and may_match pairs"""
        unique_reviews = []
        groups = []
        first_index = {}
        for review in reviews:
            sign = review["candidate"], frozenset(review["may_match"])
            if sign not in first_index:
                first_index[sign] = len(first_index)
                unique_reviews.append(review)
                groups.append([])
            groups[first_index[sign]].append(review)
        return unique_reviews, groups 

    
    
    llm = init_chat_model("google_genai:gemini-3.5-flash-lite")
    llm = llm.with_structured_output(ListReviewed)
    llm = llm.with_retry(
        stop_after_attempt=3,
        wait_exponential_jitter=True,
    )

    answers = {}
    incorrect_matching = []
    reviews, groups = collapse_reviews(reviews)
    pending = list(range(len(reviews)))

    # 3 retries
    for _ in range(3):
        if not pending:
            break

        print("Sending LLM call")
        results = llm.invoke(get_review_prompt([(i, reviews[i]) for i in pending]))
        
        for result in results.reviews:
            # Model makes up an id
            if result.id not in pending:
                continue

            # Incorrect matching
            if result.choice is not None and result.choice not in range(1, len(reviews[result.id]["may_match"]) + 1):
                pending.remove(result.id) # dont retry
                incorrect_matching.append((result, reviews[result.id]))
                continue

            # Get Chosen tech from the chosen option by the LLM 
            if result.choice is not None:
                result.final_tech = reviews[result.id]["may_match"][result.choice - 1]
            else:
                result.final_tech = None

            # Add correct answer
            answers[result.id] = result
            pending.remove(result.id)
    
    return answers, pending, incorrect_matching, groups  








papers_inserted = [
    {
        "paper_id": "1706.03762",
        "technologies": ["Transformer", "recurrent neural networks", "convolutional neural networks"],
        "category": "cs.CL",
        "summary": "The paper proposes the Transformer, a new simple network architecture based solely on attention mechanisms that dispenses with recurrence and convolutions entirely, demonstrating superior translation quality and parallelizability.",
        "research_context": ["methodological"]
    },
    {
        "paper_id": "1810.04805",
        "technologies": ["BERT", "Bidirectional Encoder Representations from Transformers"],
        "category": "cs.CL",
        "summary": "The authors introduce BERT, a language representation model designed to pre-train deep bidirectional representations from unlabeled text, which can be fine-tuned to create state-of-the-art models for a wide range of tasks.",
        "research_context": ["methodological"]
    },
    {
        "paper_id": "2005.14165",
        "technologies": ["GPT-3", "autoregressive language model"],
        "category": "cs.CL",
        "summary": "The paper demonstrates that scaling up language models, specifically by training GPT-3 with 175 billion parameters, greatly improves task-agnostic, few-shot performance.",
        "research_context": ["methodological"]
    }
]


papers_test = [
    PaperSummary(
        paper_id="1512.03385",
        technologies=[
            "ResNet",
            "Residual Network",
            "residual learning",
            "convolutional neural networks",
            "ImageNet",
        ],
        category="cs.CV",
        summary=(
            "The paper introduces residual learning, a framework that enables "
            "the training of substantially deeper neural networks by learning "
            "residual functions. The resulting ResNet architectures achieve "
            "strong image recognition performance on ImageNet and other visual "
            "recognition benchmarks."
        ),
        research_context=["methodological"],
    ),
    PaperSummary(
        paper_id="1412.6980",
        technologies=[
            "Adam",
            "Adaptive Moment Estimation",
            "stochastic gradient descent",
            "gradient-based optimization",
            "AdaMax",
        ],
        category="cs.LG",
        summary=(
            "The paper introduces Adam, an optimization algorithm that adapts "
            "learning rates using estimates of the first and second moments "
            "of gradients. It is computationally efficient and well suited "
            "to large-scale problems and noisy or sparse gradients."
        ),
        research_context=["methodological"],
    ),
    PaperSummary(
        paper_id="2005.11401",
        technologies=[
            "RAG",
            "Retrieval-Augmented Generation",
            "BART",
            "Dense Passage Retrieval",
            "Wikipedia passage index",
            "neural retriever",
        ],
        category="cs.CL",
        summary=(
            "The paper introduces retrieval-augmented generation models that "
            "combine a pretrained sequence-to-sequence generator with retrieved "
            "external documents. The approach improves performance on "
            "knowledge-intensive tasks and open-domain question answering."
        ),
        research_context=["methodological"],
    ),
]


def test():
    sim_mappings, new_keywords, to_review =  normalize(papers_test)
    print("sim_mappings")
    print(sim_mappings)

    print("new")
    print( [(n['name'], n['aliases']) for n in new_keywords])

    print("Review")
    print(to_review)

#test()