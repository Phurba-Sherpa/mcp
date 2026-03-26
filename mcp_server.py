from fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP("DocumentMCP")


docs = {
    "deposition.md": "This deposition covers the testimony of Angela Smith, P.E.",
    "report.pdf": "The report details the state of a 20m condenser tower.",
    "financials.docx": "These financials outline the project's budget and expenditures.",
    "outlook.pdf": "This document presents the projected future performance of the system.",
    "plan.md": "The plan outlines the steps for the project's implementation.",
    "spec.txt": "These specifications define the technical requirements for the equipment.",
}


# TODO: Write a tool to read a doc
@mcp.tool(
    name="read_doc",
    description="read specific document and return the content as string",
)
def read_doc(doc_id: str = Field(description="ID of the document to read")) -> str:
    if doc_id not in docs:
        raise ValueError(f"Doc with {doc_id} not found")
    return docs[doc_id]


# TODO: Write a tool to edit a doc
@mcp.tool(name="edit_doc", description="Edit the document of given ID")
def edit_doc(
    doc_id: str = Field(
        description="Replace a given part of the document with the new provided content"
    ),
    old: str = Field(description="Old content of the document to be replaced"),
    new: str = Field(description="New content to replace old content"),
):
    if doc_id not in docs:
        raise ValueError(f"Document with given ID: {doc_id} doesn't exist")
    docs[doc_id] = docs[doc_id].replace(old, new)


# TODO: Write a resource to return all doc id's
# TODO: Write a resource to return the contents of a particular doc
# TODO: Write a prompt to rewrite a doc in markdown format
# TODO: Write a prompt to summarize a doc


if __name__ == "__main__":
    mcp.run(transport="stdio")
