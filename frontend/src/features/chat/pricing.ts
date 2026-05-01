// USD pro 1M Tokens. Stand 2026-Q1. Quelle: jeweilige Provider-Pricing-Pages.
// Cache-Read = ~10% von Input; Cache-Write = ~125% von Input (Anthropic-Konvention).
export interface Pricing {
  input: number
  output: number
  cache_read?: number
  cache_write?: number
}

const PRICING: { match: RegExp; price: Pricing }[] = [
  { match: /^claude-opus-4/i,             price: { input: 15.00, output: 75.00, cache_read: 1.50,  cache_write: 18.75 } },
  { match: /^claude-sonnet-4/i,           price: { input: 3.00,  output: 15.00, cache_read: 0.30,  cache_write: 3.75  } },
  { match: /^claude-haiku-4/i,            price: { input: 1.00,  output: 5.00,  cache_read: 0.10,  cache_write: 1.25  } },
  { match: /^claude-3-7-sonnet/i,         price: { input: 3.00,  output: 15.00, cache_read: 0.30,  cache_write: 3.75  } },
  { match: /^claude-3-5-haiku/i,          price: { input: 0.80,  output: 4.00,  cache_read: 0.08,  cache_write: 1.00  } },
  { match: /^minimax-?m2/i,               price: { input: 0.30,  output: 1.20  } },
  { match: /^abab6\.5/i,                  price: { input: 0.20,  output: 0.80  } },
  { match: /^gpt-4o-mini/i,               price: { input: 0.15,  output: 0.60  } },
  { match: /^gpt-4o/i,                    price: { input: 2.50,  output: 10.00 } },
  { match: /^o1-preview/i,                price: { input: 15.00, output: 60.00 } },
  { match: /^o1-mini/i,                   price: { input: 3.00,  output: 12.00 } },
]

export function pricingFor(model?: string): Pricing | null {
  if (!model) return null
  for (const { match, price } of PRICING) {
    if (match.test(model)) return price
  }
  return null
}

export function estimateCostUsd(
  model: string | undefined,
  tokens: { input?: number; output?: number; cache_read?: number; cache_creation?: number },
): number | null {
  const p = pricingFor(model)
  if (!p) return null
  const cost =
    ((tokens.input ?? 0)         * p.input +
     (tokens.output ?? 0)        * p.output +
     (tokens.cache_read ?? 0)    * (p.cache_read ?? p.input * 0.1) +
     (tokens.cache_creation ?? 0) * (p.cache_write ?? p.input * 1.25)
    ) / 1_000_000
  return cost
}

export function formatCost(usd: number, locale: string): string {
  if (usd < 0.01) return `< $0.01`
  return `$${usd.toLocaleString(locale, { minimumFractionDigits: 2, maximumFractionDigits: usd < 1 ? 4 : 2 })}`
}
