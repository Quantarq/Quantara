import os

from web_app.contract_tools.blockchain_call import StarknetClient
from web_app.contract_tools.constants import TokenParams
from fastapi import FastAPI, Form, Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app = FastAPI()
app.mount("/static", StaticFiles(directory="web_app/static"), name="static")
CLIENT = StarknetClient()


@app.get("/{holder_address}", response_class=HTMLResponse)
async def get_form(request: Request, holder_address: str = Path(...)):
    """
    Get the form for the user to input the token, protocol, and multiplier.
    :param request: Request object
    :param holder_address: str - the address of the holder
    :return: response object
    """
    wallet_balances = {}

    # Fetch the balance for each token in TokenParams
    for token in TokenParams:
        token_address, decimals = token.value
        balance = await CLIENT.get_balance(token_addr=token_address, holder_addr=holder_address, decimals=decimals)
        wallet_balances[token.name] = balance

    # Render the template with the balances
    return templates.TemplateResponse(
        "index.html",  # Template name
        {
            "request": request,
            "holder_address": holder_address,  # Pass the holder address for reference
            "balances": wallet_balances  # Pass the calculated balances
        }
    )


@app.post("/submit")
async def submit_form(
    token: str = Form(...), protocol: str = Form(...), multiplier: int = Form(...)
):
    """
    Submit the form and return the response.
    :param token: Token address
    :param protocol: Protocol address
    :param multiplier: Multiplier
    :return: dict
    """
    return {"token": token, "protocol": protocol, "multiplier": multiplier}
