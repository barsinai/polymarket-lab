# Israel: tax and legal notes for a Polymarket market-making pilot

_Research notes, 2026-11-03. Not legal or tax advice. Written from public articles (sources at the
bottom); to be checked with an Israeli CPA/tax lawyer before any real money is used._

## The short version

1. **There is no official Israel Tax Authority (ITA) position on Polymarket.** Every source says so.
   The tax result depends on how an assessor classifies the activity, case by case.
2. **Three possible classifications**, with very different results for a market maker:

   | Classification | Rate | Losses / expenses | Fit for market making |
   |---|---|---|---|
   | Gambling / prize income (s. 2A) | 35% of the **gross** win (+ up to ~5% surtax), exemption up to ~33,840 NIS per win tapering to 0 at ~67,680 NIS — and the exemption likely does **not** apply to foreign platforms | losses and costs **not** deductible | catastrophic: we win and lose thousands of small amounts; tax on gross wins with no loss offset could exceed the whole profit |
   | Business income (s. 2(1)) | marginal rates up to 47% (+3% surtax) | expenses and losses deductible | realistic: systematic, frequent, model-driven, risk-managed activity is exactly what courts call a business |
   | Capital gains (s. 88 et seq.) | 25% (+surtax) | losses offsettable against other capital gains | possible for occasional positions; unlikely for thousands of trades a day |

   Frequency, volume, expertise, use of models and risk management push toward **business**. For a
   market maker, business treatment is probably the best outcome and also the most likely one; the
   risk to manage is an assessor reaching for s. 2A on the gross wins.
3. **Crypto layer.** The ITA treats digital currency (USDC/pUSD included) as an **asset**, not money.
   Every conversion (NIS -> USDC, USDC -> position, position -> USDC, USDC -> NIS) can be a tax
   event. With a stablecoin the gain per step is tiny (USD/NIS moves), but the **record-keeping
   duty** is real and foreign/decentralised holdings must be declared in the annual return.
4. **Banks.** Israeli banks demand the full "money trail" and sometimes an ITA confirmation before
   accepting crypto-sourced deposits. Plan the exit route (which exchange, which bank) before the
   entry.
5. **Legality of playing.** Israel bans most gambling; Penal Law s. 226 makes *playing a prohibited
   game* an offence (up to 1 year / ~29,200 NIS fine), but courts treat financial contracts
   (binary options, CFDs) as securities-law matters, not gambling, and no Israeli law, court or
   regulator has classified prediction markets. Enforcement has targeted operators and sites, not
   players. The 2026 indictments of two Israelis over Polymarket were for use of classified
   information, not for using Polymarket. Third-party sites claim Israel is not geoblocked; that
   claim is unsourced and must be checked against Polymarket's own terms.

## What this means for the pilot

- Keep a complete ledger from day one: every fill, every reward payment, every rebate, every
  conversion, with NIS values at the day's rate. (The live design already logs fills; add the
  rate.) This is what lets an accountant argue "business", and what the bank will ask for.
- Decide with a CPA **before** going live whether to run it as a sole proprietor (osek) or through
  a company, and whether to request a pre-ruling from the ITA. Reward payments are income with no
  "bet" behind them, which strengthens the business/service reading.
- Budget for ~50% tax on net profit in the business case. At the expected scale (tens of dollars a
  day) the paperwork may cost more than the tax; that is itself a go/no-go input.

## Sources

- Y-Tax, "Taxation of Polymarket" — https://y-tax.co.il/en/taxation-of-polymarket/
- Y-Tax, "Prize-Winning Activity in Israel" (s. 2A thresholds) — https://y-tax.co.il/en/prize-winning-activity/
- Bizportal, M. Ampli (Adv., CPA), 10 Feb 2026 — https://www.bizportal.co.il/general/news/article/20027531
- Maariv, 23 Feb 2026 — https://www.maariv.co.il/economy/israel/article-1288212
- Chambers Gaming Law 2025, Israel — https://practiceguides.chambers.com/practice-guides/gaming-law-2025/israel
- Crowe Israel, taxation of cryptocurrencies — https://www.crowe.com/il/insights/taxation-of-cryptocurrencies
- Jerusalem Post opinion, 12 Apr 2026 — https://www.jpost.com/opinion/article-892692
- NBC News on the 2026 indictments — https://www.nbcnews.com/world/israel/israel-charges-reservist-classified-information-bet-polymarket-rcna258709
