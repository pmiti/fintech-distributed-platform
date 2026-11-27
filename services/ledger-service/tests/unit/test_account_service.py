from decimal import Decimal

import pytest

from src.application.use_cases import AccountService
from src.domain.exceptions import (
    AccountNotFoundError,
    CurrencyMismatchError,
    InactiveAccountError,
    InsufficientFundsError,
    InvalidAmountError,
)
from src.domain.repositories import AccountRepository
from src.domain.value_objects import Money
from src.infrastructure.in_memory_repository import InMemoryAccountRepository


def usd(value: str) -> Money:
    return Money(Decimal(value), "USD")


@pytest.fixture
def repo() -> AccountRepository:
    return InMemoryAccountRepository()


@pytest.fixture
def service(repo: AccountRepository) -> AccountService:
    return AccountService(reader=repo, writer=repo)


# --- Valid operations -------------------------------------------------------
async def test_create_account_starts_empty_and_active(service: AccountService) -> None:
    account = await service.create_account("USD")
    assert account.balance == Money.zero("USD")
    assert account.is_active


async def test_get_account_returns_persisted_account(service: AccountService) -> None:
    created = await service.create_account("USD")
    assert (await service.get_account(created.id)).id == created.id


async def test_credit_then_debit(service: AccountService) -> None:
    account = await service.create_account("USD")
    await service.credit_account(account.id, usd("100.50"))
    result = await service.debit_account(account.id, usd("40.25"))
    assert result.balance == usd("60.25")
    assert (await service.get_account(account.id)).balance == usd("60.25")


async def test_debit_full_balance(service: AccountService) -> None:
    account = await service.create_account("USD")
    await service.credit_account(account.id, usd("10"))
    assert (await service.debit_account(account.id, usd("10"))).balance.is_zero()


async def test_decimal_precision_is_exact(service: AccountService) -> None:
    account = await service.create_account("USD")
    await service.credit_account(account.id, usd("0.1"))
    await service.credit_account(account.id, usd("0.2"))
    assert (await service.get_account(account.id)).balance == usd("0.3")


# --- Invalid amounts --------------------------------------------------------
def test_money_rejects_negative() -> None:
    with pytest.raises(InvalidAmountError):
        usd("-1")


def test_money_rejects_float() -> None:
    with pytest.raises(InvalidAmountError):
        Money(1.5, "USD")  # type: ignore[arg-type]


@pytest.mark.parametrize("code", ["usd", "US", "USDD", "", "12$"])
def test_money_rejects_invalid_currency(code: str) -> None:
    with pytest.raises(CurrencyMismatchError):
        Money(Decimal("1"), code)


@pytest.mark.parametrize("op", ["credit_account", "debit_account"])
async def test_zero_amount_rejected(service: AccountService, op: str) -> None:
    account = await service.create_account("USD")
    with pytest.raises(InvalidAmountError):
        await getattr(service, op)(account.id, usd("0"))


# --- Currency mismatch ------------------------------------------------------
@pytest.mark.parametrize("op", ["credit_account", "debit_account"])
async def test_currency_mismatch(service: AccountService, op: str) -> None:
    account = await service.create_account("USD")
    await service.credit_account(account.id, usd("10"))
    with pytest.raises(CurrencyMismatchError):
        await getattr(service, op)(account.id, Money(Decimal("5"), "EUR"))


# --- Insufficient funds -----------------------------------------------------
async def test_insufficient_funds_leaves_balance_untouched(service: AccountService) -> None:
    account = await service.create_account("USD")
    await service.credit_account(account.id, usd("10"))
    with pytest.raises(InsufficientFundsError):
        await service.debit_account(account.id, usd("10.01"))
    assert (await service.get_account(account.id)).balance == usd("10")


# --- Inactive accounts ------------------------------------------------------
@pytest.mark.parametrize("op", ["credit_account", "debit_account"])
async def test_inactive_account_rejects_operations(
    service: AccountService, repo: AccountRepository, op: str
) -> None:
    account = await service.create_account("USD")
    account.deactivate()
    await repo.save(account)
    with pytest.raises(InactiveAccountError):
        await getattr(service, op)(account.id, usd("1"))


# --- Not found / immutability ----------------------------------------------
async def test_unknown_account_raises(service: AccountService) -> None:
    with pytest.raises(AccountNotFoundError):
        await service.get_account("missing")


def test_money_is_immutable() -> None:
    money = usd("1")
    with pytest.raises(AttributeError):
        money.amount = Decimal("2")  # type: ignore[misc]
