from fastapi import APIRouter, Request
from langchain_core.messages import HumanMessage

from what2eat.providers.llm import create_llm

router = APIRouter(prefix='/api/diagnostics', tags=['diagnostics'])


@router.post('/models')
async def diagnose_model(request: Request):
    model = create_llm(request.app.state.settings)
    response = await model.ainvoke([HumanMessage(content='仅回复 OK')])
    return {'ready': True, 'model': request.app.state.settings.llm_model,
            'response': str(response.content)[:100], 'may_incur_cost': True}
