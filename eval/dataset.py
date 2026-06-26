"""Gold dataset mapping queries to the knowledge source(s) that should answer them."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class GoldItem(BaseModel):
    """A query and the set of source filenames considered relevant."""

    model_config = ConfigDict(frozen=True)

    query: str
    relevant_sources: set[str]


# Sources correspond to the files in data/static/. Each chunk carries its source filename,
# so retrieval is scored by whether the right document was surfaced.
DEFAULT_DATASET: tuple[GoldItem, ...] = (
    GoldItem(query="Where is the parking garage located?", relevant_sources={"location.md"}),
    GoldItem(query="How do I get there by public transport?", relevant_sources={"location.md"}),
    GoldItem(
        query="How do I make a reservation?",
        relevant_sources={"reservation_process.md"},
    ),
    GoldItem(
        query="What details do you need to book a parking space?",
        relevant_sources={"reservation_process.md"},
    ),
    GoldItem(query="What is the maximum vehicle height?", relevant_sources={"rules.md"}),
    GoldItem(query="Can I park in an accessible bay?", relevant_sources={"rules.md"}),
    GoldItem(
        query="How many parking spaces are there?",
        relevant_sources={"general_info.md"},
    ),
    GoldItem(
        query="Is the car park covered and monitored?",
        relevant_sources={"general_info.md"},
    ),
)
