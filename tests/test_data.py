from backend.database import *



def test_sql():
     paper = Paper(
         id="644",
         title="Why Keria is the GOAT support",
         abstract="He is HIM",
         category="facts",
         authors="Career,TDuck",
         pub_date="2020-02-19" 
    )

     if paper.id not in get_papers_id():
          add_paper(paper)     

     assert paper.id in get_papers_id()   
