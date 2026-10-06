from langgraph.graph import StateGraph, MessagesState, START, END
from typing import TypedDict
from controller import Controller
from database import Paper

class State(TypedDict):
    new_papers: list[Paper]
    found_new: bool = False
    status: str = "Not found"


def search_for_papers(state: State):
    return { "new_papers": Controller().get_papers()}


def process_papers(state: State):
    return {"status": "found"}


def route_on_papers(state: State):
    if state["new_papers"]:
        return "process"
    return "end"


graph = StateGraph(State)

graph.add_node("search", search_for_papers)
graph.add_node("process", process_papers)

graph.add_edge(START, "search")

graph.add_conditional_edges(
    "search",
    route_on_papers,
    {
        "process": "process",
        "end": END
    }
)

graph.add_edge("process", END)

app = graph.compile()

res = app.invoke({"new_papers": [], "found_new": False})
print(res)