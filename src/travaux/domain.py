"""Small, provider-independent rules for the fictitious municipal pilot."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
import unicodedata


class DomainError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False, default=lambda x: str(x) if isinstance(x, Decimal) else _unsupported(x))


def _unsupported(value):
    raise TypeError(f'Unsupported JSON value: {type(value).__name__}')


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def payload_hash(payload) -> str:
    return content_hash(canonical_json(payload))


def normalized(text: str) -> str:
    decomposed = unicodedata.normalize('NFKD', text)
    return ' '.join(''.join(c for c in decomposed if not unicodedata.combining(c)).casefold().split())


def require_text(value, field: str, *, maximum: int = 10000, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()) or len(value) > maximum:
        raise DomainError('invalid_input', f'Champ {field} absent, invalide ou trop long.')
    return value


@dataclass(frozen=True)
class Money:
    amount: Decimal | str
    currency: str = 'EUR'
    basis: str = 'UNKNOWN'

    def __post_init__(self):
        if isinstance(self.amount, (float, bool)):
            raise DomainError('invalid_amount', 'Utiliser une chaîne décimale exacte, pas un flottant.')
        try:
            raw = str(self.amount).replace('\u00a0', '').replace('\u202f', '').replace(' ', '').replace(',', '.')
            amount = Decimal(raw)
            if not amount.is_finite() or abs(amount) > Decimal('1000000000000'):
                raise InvalidOperation
            if amount != amount.quantize(Decimal('.01')):
                raise InvalidOperation
        except (InvalidOperation, ValueError, TypeError):
            raise DomainError('invalid_amount', 'Montant décimal fini, au centime, attendu.') from None
        if self.currency != 'EUR' or self.basis not in ('HT', 'TTC', 'UNKNOWN'):
            raise DomainError('invalid_amount', 'Devise EUR et base HT, TTC ou UNKNOWN attendues.')
        object.__setattr__(self, 'amount', amount.quantize(Decimal('.01')))

    def as_dict(self) -> dict:
        return {'amount': format(self.amount, '.2f'), 'currency': self.currency, 'basis': self.basis}


def normalize_value(kind: str, value):
    if value is None:
        return None
    if kind == 'money':
        if not isinstance(value, dict):
            raise DomainError('invalid_amount', 'Un montant exige amount, currency et basis.')
        return Money(value.get('amount'), value.get('currency', 'EUR'), value.get('basis', 'UNKNOWN')).as_dict()
    if kind == 'date':
        if not isinstance(value, str):
            raise DomainError('invalid_date', 'Une date ISO ou une valeur inconnue est attendue.')
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError:
            raise DomainError('invalid_date', 'Date ISO YYYY-MM-DD invalide ; ne pas inventer de date.') from None
    if kind == 'boolean':
        if type(value) is not bool:
            raise DomainError('invalid_input', 'Booléen strict attendu.')
        return value
    if kind not in ('text', 'status', 'unknown'):
        raise DomainError('invalid_input', 'Type de fait non pris en charge.')
    if kind == 'unknown':
        raise DomainError('invalid_input', 'Une valeur inconnue doit être null.')
    return require_text(value, 'value')


def validate_field(field: str) -> str:
    if not isinstance(field, str) or not re.fullmatch(r'[a-z][a-z0-9_.-]{0,63}', field):
        raise DomainError('invalid_input', 'Identifiant de champ métier invalide.')
    return field


def evidence_span(source: dict, quote: str, start: int | None = None, end: int | None = None,
                  expected_hash: str | None = None) -> dict:
    require_text(quote, 'quote', maximum=100000)
    body = source['body']
    if expected_hash is not None and expected_hash != source['body_hash']:
        raise DomainError('invalid_evidence', 'La version de la preuve ne correspond pas.')
    if start is None:
        start = body.find(quote)
    if type(start) is not int or (end is not None and type(end) is not int):
        raise DomainError('invalid_evidence', 'Les bornes de citation doivent être des entiers.')
    if end is None:
        end = start + len(quote)
    if type(start) is not int or type(end) is not int or start < 0 or end <= start or end > len(body) or body[start:end] != quote:
        raise DomainError('invalid_evidence', 'Citation absente ou bornes incompatibles avec cette source.')
    return {'source_id': source['id'], 'source_hash': source['body_hash'],
            'start': start, 'end': end, 'quote': quote}
