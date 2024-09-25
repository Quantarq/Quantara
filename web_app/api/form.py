from fastapi.templating import Jinja2Templates
from fastapi import Form, APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.requests import Request
from datetime import datetime

from web_app.contract_tools.constants import TokenParams
from web_app.contract_tools.utils import DashboardMixin, DepositMixin

# Initialize the client and templates
templates = Jinja2Templates(directory="web_app/api/templates")
router = APIRouter()  # Initialize the router


@router.get("/", response_class=HTMLResponse)
async def get_form(request: Request):
    """
    Fetch wallet balances and render the form.
    Get the form to submit the token, protocol, and multiplier.
    :param request: Request object
    :return: TemplateResponse
    """
    # Check if the wallet_id is in session
    session_wallet_id = request.session.get("wallet_id")
    if session_wallet_id:
        holder_address = session_wallet_id
    else:
        # Redirect to login if no wallet_id in session
        return RedirectResponse(url="/login", status_code=302)

    # Fetch the balance for each token in TokenParams
    wallet_balances = await DashboardMixin.get_wallet_balances(holder_address)

    # Render the template with the balances
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "holder_address": holder_address,
            "balances": wallet_balances,
        },
    )


multipliers = {}
start_dates = {}


@router.post("/submit")
async def submit_form(
    token: str = Form(...),
    multiplier: int = Form(...),
):
    # Save submitted form data
    multipliers[token] = multiplier
    start_dates[token] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Redirect to the dashboard
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/dashboard")
async def get_dashboard(request: Request):
    """
    Get the dashboard with the balances, multipliers, and start dates.
    :param request: HTTP request
    :return: template response
    """
    # Pass balances, multipliers, and start_dates to the template
    wallet_id = request.session.get("wallet_id")
    if not wallet_id:
        return RedirectResponse("/login", status_code=302)

    wallet_balances = await DashboardMixin.get_wallet_balances(wallet_id)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "balances": wallet_balances,
            "multipliers": multipliers,
            "start_dates": start_dates,
        },
    )


@router.get("/transaction-data")
async def get_transaction_data(request: Request, token: str, multiplier: int, amount: int):
    return await DepositMixin.get_transaction_data(
        token, amount, multiplier, request.session["wallet_id"], TokenParams.USDC.value[0]
    )
