from src.utils.prompt_utils import format_prompt


def RERANKER_SYSTEM_PROMPT() -> str:
    return format_prompt(
        """
You are a search engine assistant tasked with reranking code search results based on their relevance to a given query.
Your goal is to determine which results are most relevant for implementing the requested changes.
"""
    )


def RERANKER_USER_PROMPT(objective: str, results: str) -> str:
    return format_prompt(
        f"""
Given the list of code search results, produce an array of scores measuring the relevance of each search result for implementing the following changes:

<objective>
{objective}
</objective>

Here are the search results:
<search_results>
{results}
</search_results>

Prune the results to only include relevant results that will help implement the objective.

For each relevant result, provide:
1. Your thought process for choosing this score
2. The file path of the search result for file lookup
3. The id of the search result
4. A score between 0 and 100

A score must be between 0 and 100 for each result, where 100 is extremely relevant and 0 is not relevant at all.

When returning file paths, only return the file path so we can look them up, no line numbers or other text. (i.e app/page.tsx, not app/page.tsx:59-106).
Results should be returned in the order of relevance, most relevant first.
"""
    )
