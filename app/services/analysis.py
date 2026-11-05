import asyncio

from app.services.risk_classifier import classify_clause
from app.services.clause_filter import informational_reason


async def analyze_clauses(clauses: list[dict], semaphore: asyncio.Semaphore) -> list[dict]:

    async def analyze(clause):
        reason = informational_reason(clause["text"])
        if reason:
            return {**clause, "type": "informational", "skip_reason": reason, "result": None}
        async with semaphore:
            result = await asyncio.to_thread(classify_clause, clause["text"])
            return {**clause, "type": "risk_analysis", "skip_reason": None, "result": result}

    tasks = [asyncio.create_task(analyze(clause)) for clause in clauses]
    try:
        return await asyncio.gather(*tasks)
    except BaseException:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
