---
category: purchase_method
context:
  state: '*'
  contract_type: purchase_agreement
  purchase_method: auction
  use_category: '*'
  user_experience: '*'
  analysis_depth: '*'
priority: 70
version: 1.0.0
description: Auction-specific considerations and focus areas for purchase agreements
tags:
- purchase
- method
- auction
type: fragment
name: purchase_method_auction_considerations
---

### Auction Method: Key Considerations
- Unconditional on fall of hammer unless expressly stated; finance and inspection conditions generally not available.
- Cooling-off periods typically do not apply; verify state-specific exceptions.
- Deposit payable immediately on sale (commonly 10%, or as specified); ensure acceptable payment methods are documented.
- Review auction conditions of sale (vendor bids, reserve price, bidder registration requirements).
- Confirm settlement timeframe, adjustments, inclusions/exclusions, and special conditions pre-auction.
- Complete due diligence (building/pest, finance pre-approval, searches) before auction day.
- Clarify authority of auctioneer and handling of disputes, late bids, or variations.

### OCR/Extraction Focus
- Identify references to “auction conditions”, reserve price, bidder registration, and vendor bid clauses.
- Extract deposit percentage/amount and due time (immediate vs within X business days).
- Capture settlement date/period and any non-standard special conditions.
- Detect statements excluding cooling-off or contingent conditions.

