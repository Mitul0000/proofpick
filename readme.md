• # Product Research and Evaluation Assistant

  ## 1. Project objective

  The product is an AI-powered research assistant that evaluates any
  product according to the user’s needs.    

  A user can:

  - Ask for the best product for a specific purpose.
  - Provide a product name and request an evaluation.
  - Compare a product with alternatives.
  - Specify budget, location, required features, and priorities.
  - Receive a recommendation supported by web and YouTube research.

  The system should explain not only which product is recommended, but
  also:

  - Why it is suitable
  - Where it performs well
  - Its weaknesses
  - Which alternatives are better in specific areas
  - What compromises are required
  - Which sources were consulted
  - How reliable and recent the evidence is
  - Where information conflicts or is uncertain

  ———

  # 2. Complete user flow

  ## Step 1: User starts a conversation

  The user communicates with a chatbot through the frontend.

  Examples:

  - “I want a phone for gaming under ₹20,000.”
  - “Evaluate this laptop for programming and video editing.”
  - “Is this washing machine good for a family of four?”
  - “Compare this camera with its alternatives.”

  The frontend sends each message to the Python backend.

  ———

  ## Step 2: The system understands the user’s intention


  ## Json 
  ---------------------------------

    {
    "session_id": "string",
    "conversation_state": "gathering_requirements | ready_for_research | researching | completed",
    "last_updated": "ISO-8601 timestamp",

    "request_type": "recommendation | evaluation | comparison",
    "product_category": "string (free text, e.g. 'smartphone', 'pen', 'washing_machine')",
    "category_confidence": 0.0,

    "named_products": [
        {
        "raw_text": "string (exactly what user typed)",
        "brand": "string | null",
        "model": "string | null",
        "variant": "string | null",
        "match_confidence": 0.0,
        "role": "primary | comparison_target | alternative_mentioned"
        }
    ],

    "user_context": {
        "purpose": [
        { "label": "string", "importance": "primary | secondary" }
        ],
        "budget": {
        "min": null,
        "max": null,
        "currency": "string (ISO 4217)",
        "flexibility": "strict | somewhat_flexible | unknown"
        },
        "location": {
        "country": "string | null",
        "region": "string | null",
        "market_notes": "string | null"
        },
        "usage_pattern": {
        "frequency": "string | null",
        "environment": "string | null",
        "user_experience_level": "beginner | intermediate | expert | unknown"
        }
    },

    "required_features": [
        {
        "attribute": "string",
        "constraint": "string",
        "hard_requirement": true,
        "source_turn": 0
        }
    ],

    "preferred_features": [
        {
        "attribute": "string",
        "preference": "string",
        "hard_requirement": false
        }
    ],

    "priorities": [
        { "attribute": "string", "weight": 0.0 }
    ],

    "excluded_options": {
        "brands": [],
        "products": [],
        "reasons": {}
    },

    "comparison_products": [
        { "raw_text": "string", "brand": "string | null", "model": "string | null" }
    ],

    "missing_fields": [
        { "field": "string", "question_priority": "high | medium | low" }
    ],

    "resolved_slots": {
        "budget_known": false,
        "purpose_known": false,
        "priorities_known": false,
        "category_known": false,
        "sufficient_for_research": false
    },

    "notes": "string | null"
    }

  --------------------------------

  The LLM analyzes the message and identifies:

  - What product category is involved
  - Whether the user wants a recommendation, evaluation, or comparison
  - Whether a specific product was named
  - The user’s main purpose
  - Budget and location
  - Required features
  - Preferred features
  - Important compromises
  - Missing information

  The LLM does not perform the full research at this stage. It only
  understands the request and converts it into usable internal
  information.

  ———

  ## Step 3: The chatbot asks follow-up questions

  The backend checks whether enough information is available.

  For example, if the user says:

  > “Suggest me a laptop.”

  The chatbot may ask:

  - What is your budget?
  - What will you mainly use it for?
  - Do you need gaming performance?
  - How important are battery life and portability?
  - Do you have any preferred brands?

  The questions are based on the product category and predefined
  research requirements.

  The system should not ask unnecessary questions. It should stop asking
  when it has enough information to produce a meaningful evaluation.

  ———

  ## Step 4: The system prepares the research plan

  Once the requirements are sufficient, the LLM creates a research plan.

  The plan includes:

  - Main product name
  - Product category
  - Exact model and variant
  - User priorities
  - Important attributes to investigate
  - Alternative products to find
  - Search terms for Google
  - Search terms for YouTube
  - Research depth

  For example, a gaming-phone research plan may include:

  - Gaming performance
  - Processor
  - Thermal behavior
  - Battery
  - Charging speed
  - Display
  - Software support
  - Current price
  - Common problems
  - Alternative gaming phones

  The LLM generates multiple focused search queries instead of one broad
  query.

  ———

  ## Step 5: The system searches the web and YouTube

  The backend sends the generated queries to search services.

  It collects:

  - Search result titles
  - URLs
  - Snippets
  - Domains
  - Publication dates
  - Product names
  - YouTube video titles
  - Video descriptions
  - Channel names
  - Available transcripts
  - View and engagement information where available

  The system should use permitted APIs and respect website rules, rate
  limits, and access restrictions.

  ———

  ## Step 6: The system filters search results

  The system should not process every result.

  Each URL is given a source-selection score based on:

  - Relevance to the search query
  - Exact product-name match
  - Product variant match
  - Source type
  - Freshness
  - Expected attribute coverage
  - Domain reliability
  - Duplicate content
  - Existing number of results from that domain

  The system also maintains source diversity.

  For example, it may select:

  - Official product sources
  - Independent review websites
  - Technical testing websites
  - Retailers
  - Community discussions
  - YouTube reviews

  This is better than selecting only the websites with the highest SEO
  authority.

  ———

  ## Step 7: The system evaluates source quality

  The system records information about every selected source.

  It evaluates:

  - Type of source
  - Domain history
  - Technical detail
  - Whether the author performed firsthand testing
  - Publication date
  - Commercial or affiliate bias
  - Transparency about sponsorship
  - Agreement with other independent sources
  - Whether the page appears copied or low quality

  Optional third-party metrics may be collected from services such as:

  - Moz
  - Ahrefs
  - Semrush
  - Majestic

  These services provide SEO-related metrics such as Domain Authority,
  Domain Rating, Authority Score, Trust Flow, and Citation Flow.

  However, these metrics do not prove that a review is factually
  accurate. They should be treated as one supporting signal, not as the
  final trust score.

  The system should create its own claim-specific reliability score.

  For example:

  - Official source: highly reliable for specifications
  - Retailer: highly useful for price and availability
  - Independent review: useful for practical experience
  - YouTube reviewer: useful for demonstrations and hands-on
    observations

  - Community post: useful for discovering repeated problems, but weaker
    as individual evidence

  ———

  ## Step 8: The system cleans the content

  The selected pages are downloaded or accessed through permitted
  methods.

  The backend removes:

  - Navigation
  - Advertisements
  - Cookie messages
  - Repeated headers and footers
  - Related links
  - Irrelevant comments
  - Duplicate text
  - Unrelated sections

  For YouTube, the system primarily uses:

  - Title
  - Description
  - Chapters
  - Transcript
  - Relevant transcript segments

  It does not need to send complete videos to an LLM.

  ———

  ## Step 9: The system chunks the content

  The cleaned text is divided into smaller sections.

  Each chunk is stored with:

  - Source ID
  - URL
  - Product name
  - Document title
  - Position in the document
  - Publication date
  - Content type

  Chunking makes it possible to process large numbers of documents
  without exceeding model context limits.

  ———

  ## Step 10: The system retrieves only relevant chunks

  The backend creates vector embeddings for the chunks.

  It also creates embeddings for:

  - User requirements
  - Product name
  - Search queries
  - Important attributes

  The system uses vector similarity and keyword matching to retrieve
  only chunks relevant to the current evaluation.

  For example, if the user cares about battery life and gaming, chunks
  about camera design or packaging may be ignored.

  Hybrid retrieval is preferable:

  - Keyword matching finds exact model names and specifications.
  - Vector search finds semantically related passages.
  - Product and attribute matching prevents unrelated results.

  ———

  ## Step 11: The system extracts structured claims

  The relevant chunks are sent to a small or inexpensive extraction
  model.

  The model extracts only information explicitly present in the text,
  such as:

  - Battery capacity
  - Measured battery life
  - Gaming performance
  - Heating
  - Camera quality
  - Build quality
  - Price
  - Durability concerns
  - Common complaints
  - Positive observations

  The model should not write the final review at this stage.

  It should produce small factual claims, each connected to:

  - The product
  - The attribute
  - The extracted value
  - The evidence passage
  - The source
  - The confidence level
  - Whether the claim is positive, negative, or neutral

  A common claim format should be used across products. Category-
  specific attributes can be added, but arbitrary JSON structures should
  be avoided because they make comparison difficult.

  ———

  ## Step 12: The system normalizes the extracted data

  Different sources may describe the same fact differently.

  The backend converts them into consistent values.

  Examples:

  - “5,000 mAh”
  - “5000mah”
  - “5000 milliamp-hour battery”

  become the same normalized value.

  The system also normalizes:

  - Currency
  - Units
  - Storage capacity
  - Screen size
  - Ratings
  - Dates
  - Product names
  - Model variants
  - Measurement types

  This step is performed mainly with Python rules, not with an LLM.

  ———

  ## Step 13: The system removes duplicate claims

  Many websites copy specifications or reproduce the same press release.

  The backend detects:

  - Identical claims
  - Similar text
  - Duplicate URLs
  - Syndicated articles
  - Repeated information from the same source network

  Ten websites repeating one manufacturer specification should not be
  counted as ten independent confirmations.

  The system groups similar claims and records the number of independent
  sources supporting them.

  ———

  ## Step 14: The system resolves conflicts

  Different sources may report different information.

  For example:

  - One reviewer reports eight hours of battery life.
  - Another reports ten hours.
  - A third reports seven and a half hours.

  The system should not silently choose one value.

  It should calculate:

  - Common range
  - Preferred estimate
  - Number of independent sources
  - Agreement level
  - Likely reason for disagreement
  - Confidence level

  The final report should explain that results vary according to test
  method, software version, region, or usage pattern.

  ———

  ## Step 15: The system aggregates evidence

  The backend summarizes the claims into compact evidence groups.

  Each attribute receives:

  - Normalized result
  - Supporting sources
  - Contradictory sources
  - Source count
  - Independent source count
  - Confidence
  - Freshness
  - Positive and negative evidence

  This aggregation happens before the final LLM call.

  Therefore, the final LLM receives organized evidence instead of
  hundreds of full pages.

  ———

  ## Step 16: The system scores each product

  The scoring engine compares every product against the user’s
  priorities.

  It evaluates:

  - Required criteria
  - Optional criteria
  - Budget
  - Intended use
  - Feature quality
  - Practical performance
  - Evidence confidence
  - Known compromises

  The user’s priorities are converted into weights.

  For example:

  Performance: 40%
  Battery: 25%
  Price: 20%
  Camera: 15%

  The system calculates a score for every criterion and then creates a
  weighted overall score.

  Mandatory requirements are checked separately. A product that violates
  a hard requirement should not be recommended as the primary choice,
  even if its overall score is high.

  ———

  ## Step 17: The system finds alternatives

  The system searches for products that are:

  - In the same category
  - Within a similar budget
  - Suitable for the same use case
  - Strong in areas where the original product is weak

  Alternatives are not selected simply because they appear frequently in
  search results.

  They are evaluated using the same evidence and scoring process.

  The result may show:

  - Best overall match
  - Best value
  - Best performance
  - Best battery
  - Best alternative for a specific compromise

  ———

  ## Step 18: The final LLM generates the report

  The final LLM receives only the compact aggregated evidence.

  It receives:

  - User requirements
  - Product scores
  - Main strengths
  - Main weaknesses
  - Alternatives
  - Important conflicts
  - Confidence values
  - Source details
  - Citation links

  The final model is instructed to:

  - Use only the supplied evidence
  - Never invent specifications
  - Clearly separate fact and interpretation
  - Explain trade-offs
  - Mention uncertainty
  - Cite important statements
  - Avoid treating popularity as proof

  The ranking is calculated by the backend. The LLM mainly explains the
  result in natural language.

  ———

  ## 19. The user receives the final report

  The report may contain:

  - Final verdict
  - Why the product matches the user
  - Main advantages
  - Main disadvantages
  - Best alternatives
  - Comparison table
  - Compromises
  - Source list
  - Source reliability information
  - Conflicting evidence
  - Research date
  - Confidence level

  For long research, the frontend should show progress:

  - Searching sources
  - Processing pages
  - Analyzing videos
  - Comparing evidence
  - Generating report

  ———

  # 20. Cost-control strategy

  The system should use different models for different tasks.

  Use a small or local model for:

  - Intent detection
  - Missing-information detection
  - Query classification
  - Chunk relevance classification
  - Claim extraction

  Use Python for:

  - Filtering
  - Normalization
  - Deduplication
  - Source scoring
  - Product scoring
  - Conflict calculations
  - Database operations

  Use a stronger model only for:

  - Complex synthesis
  - Final explanation
  - Difficult ambiguity resolution

  Also use:

  - Search-result caching
  - Page-content caching
  - Content hashes
  - Embedding caching
  - Duplicate detection
  - Research-depth limits
  - Background workers
  - Reuse of previously extracted evidence

  The system can offer:

  Quick research
  Standard research
  Deep research

  ———

  # 21. Backend architecture

  The initial backend can contain:

  - Conversation manager
  - Requirement manager
  - Query generator
  - Search service
  - YouTube service
  - Page extractor
  - Chunking service
  - Embedding service
  - Claim extractor
  - Normalization service
  - Deduplication service
  - Source-quality service
  - Scoring engine
  - Report generator
  - Research job manager
  - Database and cache layer

  FastAPI can expose the application endpoints, while background workers
  handle long-running research.

  ———

  # 22. Conversation and research behavior

  Every user message is sent to the backend.

  The backend:

  1. Loads the conversation state.
  2. Adds the new message.
  3. Calls an appropriate model.
  4. Updates the requirements.
  5. Decides whether to ask a question or start research.
  6. Saves the response and state.

  Research should run as a background job rather than keeping one HTTP
  request open for a long time.

  ———

  # 23. MCP integration

  The core product should first be built as normal reusable Python
  services.

  Later, an MCP server can expose those services as tools.

  For example:

  - Start product research
  - Check research status
  - Retrieve evidence
  - Compare products
  - Retrieve source information
  - Generate a report

  The web application and MCP server should both call the same core
  functions.

  The application should not call its own MCP server internally, because
  that adds unnecessary complexity.

  ———

  # 24. Development plan

  ## Phase 1: Basic chatbot

  - Conversation handling
  - Requirement extraction
  - Follow-up questions
  - Structured internal state
  - No large-scale research yet

  ## Phase 2: One product category

  Start with a category such as smartphones.

  - Google search
  - YouTube search
  - Page cleaning
  - Chunking
  - Claim extraction
  - Basic citations

  ## Phase 3: Evidence and scoring

  - Source filtering
  - Source reliability
  - Claim deduplication
  - Conflict detection
  - Product scoring
  - Alternative selection

  ## Phase 4: Cost and scale

  - Caching
  - Background workers
  - Local embeddings
  - Smaller local extraction model
  - Research-depth controls
  - Rate-limit handling

  ## Phase 5: Generic product categories

  Add category-specific evaluation criteria for:

  - Laptops
  - Cameras
  - Cars
  - Appliances
  - Headphones
  - Other products

  ## Phase 6: MCP server

  Expose the existing research functions through MCP for use by other AI
  clients.

  ———

  # 25. Main principle

  The complete system should work like this:

  The LLM understands the user.
  The search system collects sources.
  The retrieval system finds relevant passages.
  The extraction model converts passages into claims.
  Python organizes, scores, verifies, and aggregates the claims.
  The final LLM explains the evidence and recommendation.

  This division keeps the system cheaper, more transparent, easier to
  debug, and more trustworthy than sending all web and YouTube content
  directly to one large model.
