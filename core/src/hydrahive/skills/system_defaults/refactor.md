---
name: refactor
description: Refaktoriert Code zur Qualitätsverbesserung — SOLID-Prinzipien, Code-Smells entfernen, bessere Patterns vorschlagen. Für Verbesserung der Code-Struktur oder Modernisierung von Legacy-Code.
when_to_use: Wenn Funktionen zu lang sind, Klassen zu viel tun, Code dupliziert ist, oder Legacy-Code für neue Features vorbereitet werden muss.
tools_required: [read_file, write_file, grep, glob]
---

# Code-Refactoring-Skill

## 1. Extract Method — eine Sache pro Funktion

```python
# Vorher: eine große Funktion die alles macht
def process_order(order):
    total = 0
    for item in order.items:
        total += item.price * item.quantity
    total *= 1.08
    send_email(order.customer.email, f"Total: ${total}")

# Nachher: kleine fokussierte Funktionen
def process_order(order):
    total = _calculate_total(order.items)
    _send_confirmation(order, total)

def _calculate_total(items, tax_rate=0.08):
    return sum(i.price * i.quantity for i in items) * (1 + tax_rate)
```

## 2. Guard Clauses — Nesting entfernen

```python
# Vorher: tief verschachtelt
def process(payment):
    if payment:
        if payment.amount > 0:
            if payment.method:
                return charge(payment)

# Nachher: flat mit frühen Returns
def process(payment):
    if not payment:
        raise ValueError("No payment")
    if payment.amount <= 0:
        raise ValueError("Invalid amount")
    if not payment.method:
        raise ValueError("No method")
    return charge(payment)
```

## 3. Magic Numbers ersetzen

```python
# Vorher
if price > 100:
    return price * 0.15

# Nachher
DISCOUNT_THRESHOLD = 100
PREMIUM_RATE = 0.15
STANDARD_RATE = 0.05

rate = PREMIUM_RATE if price > DISCOUNT_THRESHOLD else STANDARD_RATE
return price * rate
```

## 4. Klassen aufteilen — eine Verantwortung pro Klasse

```python
# Vorher: God-Class
class Order:
    customer_name = ""
    customer_email = ""
    shipping_method = ""
    shipping_cost = 0

# Nachher: getrennte Verantwortungen
class Customer:
    def __init__(self, name, email): ...

class Shipping:
    def __init__(self, method, cost): ...

class Order:
    def __init__(self, customer: Customer, shipping: Shipping): ...
```

## 5. Dependency Injection

```python
# Vorher: hardcodierte Dependency — untestbar
class UserService:
    def __init__(self):
        self.db = Database()

# Nachher: injiziert — testbar, austauschbar
class UserService:
    def __init__(self, database):
        self.db = database
```

## 6. Duplikate entfernen (DRY)

```python
# Vorher: gleiche Struktur zweimal
def send_welcome(user):
    send_email(user.email, "Welcome!", f"Hello {user.name}")

def send_reset(user):
    send_email(user.email, "Reset", f"Hello {user.name}, reset here")

# Nachher
def _send_user_email(user, subject, body_template):
    send_email(user.email, subject, body_template.format(name=user.name))
```

## 7. Refactoring-Checkliste

Vor dem Refactoring:
- Tests vorhanden und grün? (Sicherheitsnetz)
- Code vollständig verstanden?
- Immer nur eine Änderung auf einmal

Nach jedem Schritt:
- Tests noch grün?
- Code lesbarer?
- Kein neues Verhalten hinzugefügt?

## HydraHive-spezifische Regeln

- Max ~200 Zeilen pro Datei — bei Überschreitung aufteilen
- Co-location: zusammengehöriger Code liegt zusammen
- Keine hardcodierten Pfade — Settings-Singleton nutzen
- Keine zirkulären Imports
