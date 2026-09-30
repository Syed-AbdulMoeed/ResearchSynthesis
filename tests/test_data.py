from backend.database import *



def test_sql():
     paper = Paper(
         id="60",
         title="Why Keria is the GOAT support",
         summary="He is HIM",
         category="facts",
         authors="Career,TDuck",
         pub_date="2020-02-18" 
    )

     if paper.id not in get_papers_id():
          add_paper(paper)     

     assert paper.id in get_papers_id()   

test_sql()