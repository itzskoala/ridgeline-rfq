# Decisions

## Time Spent

- Approximately **6 hours** total, including architecture planning, implementation, testing, debugging, and AI experimentation.

## 1. Something in the Data That Surprised Me

- One thing that caught me off guard was how much context was spread across email replies and related messages.
- An individual email did not always contain the complete RFQ. Important information could be found in previous messages, replies, or references to other emails within the same thread.
- This made email threading and context recognition more important than I initially anticipated.
- I had to account for relationships between emails rather than treating every message as an independent request.
- This influenced how I approached ingestion, thread grouping, and the AI extraction layer. The system needed to understand the surrounding conversation before extracting the final request.

## 2. Something in the Brief or README I Disagreed With

- I disagreed with JSON being the primary final deliverable for a business-facing application.
- JSON is useful for structured data exchange and communication between software components, but it is not necessarily the most practical format for the people actually using the extracted information.
- In a real distribution or sales environment, I would rather have the results exported into Excel or integrated directly into a company's existing CRM format.
- Sales representatives should be able to review RFQs, quantities, specifications, and customer information without having to interact with raw JSON.
- I kept the structured JSON output for this implementation because it provides a consistent format for validation and downstream processing.
- With more time, I would add an export layer that converts the structured results into Excel spreadsheets or a custom CRM-compatible format.

## 3. Predicted Held-Out Performance

My expectation is that the system will perform well on held-out emails, although I expect some degradation compared to the development set.

My predictions:

| Metric | Development | Held-out prediction |
|---|---:|---:|
| Classification | 24/24 | 22–24/24 |
| Line recall | 210/210 | 90–95% |
| Hallucinated lines | 0 | Very few |
| Must-mention | 421/425 | 95–98% |
| Needs review match | 22/24 | 85–90% |

These are estimates, not measured results.

**Why I expect reasonable performance:**

- The system uses email context and related messages instead of relying exclusively on individual email bodies.
- The AI extraction layer has flexibility in its prompts, allowing adjustments for different email structures and ways customers describe products.
- Structured output and schema validation help maintain consistency.
- The existing answer key and test cases provide a baseline for evaluating changes rather than relying on subjective assessments of the model's output.
- I expect the biggest performance differences to come from unfamiliar product descriptions, unusual abbreviations, OCR errors, and emails with incomplete specifications.

**Two types of emails I expect to get wrong:**

1. **Scanned or handwritten RFQs:** OCR errors, unclear handwriting, and ambiguous quantities could cause incorrect line-item extraction or unnecessary review flags.

2. **Unusual product specifications:** Customers may describe the same material or fitting using abbreviations or terminology that the system has not encountered before. These could result in missing required specifications or incorrect normalization.

## 4. How This Runs for Real

My overall opinion is that the current architecture provides a reasonable foundation for real-world use. Most additional work would involve production infrastructure, prompt refinement, and handling less common edge cases.

- **3,000 emails per day through a webhook:**
  - The current implementation processes emails synchronously from a directory in a single process.
  - For production, I would introduce a webhook endpoint that receives incoming messages and places them into a queue.
  - Background workers would process emails independently, allowing the system to handle larger volumes without blocking incoming requests.
  - I would also introduce persistent processing status and delivery-level deduplication.

- **Model provider unavailable for two hours:**
  - The current implementation has a safe fallback that returns a `needs_review` result when extraction fails.
  - For a production system, I would not rely exclusively on that fallback.
  - I would introduce retry logic with exponential backoff and a dead-letter queue for emails that repeatedly fail.
  - This would allow emails to be processed once the provider becomes available instead of permanently losing successful extraction opportunities during an outage.

- **A customer sends a 300-page PDF:**
  - The current document-reading pipeline supports extracting document content and passing it to the AI layer.
  - However, I would not assume that a 300-page document can reliably fit into a single model request.
  - I would introduce document chunking, page limits, and targeted extraction to control token usage and processing time.
  - Large documents would also need testing for OCR performance, context limits, and API costs.

- **The same email is delivered twice:**
  - The current implementation handles duplicate RFQ content within the development dataset by identifying duplicates and preferring the later email.
  - However, identical webhook deliveries are a separate problem.
  - For production, I would use the email Message-ID as an idempotency key to prevent the same message from being processed multiple times.
  - This would complement the existing duplicate-content logic rather than replace it.

## 5. Design Notes

- **Model versus code responsibilities:**
  - The AI handles understanding email context, classifying requests, and extracting structured line items.
  - Python handles deterministic operations such as ingestion, thread grouping, duplicate handling, schema validation, and output formatting.
  - I prefer keeping predictable business logic in Python rather than asking the model to make every decision.

- **AI extraction approach:**
  - I explored different implementations of the AI layer rather than committing to the first approach.
  - I ultimately preferred a simpler Python-based approach for identifying relevant request candidates and passing them directly into the extraction prompt.
  - This avoids unnecessary tool-calling complexity and gives the model the relevant email context directly.
  - It also makes the extraction flow easier to understand, test, and maintain.

- **Testing and evaluation:**
  - I used the development answer key and test cases as my primary evaluation criteria.
  - I measured classification accuracy, line recall, hallucinated line items, required specification coverage, and review-flag accuracy.
  - I manually inspected incorrect results and refined the implementation based on actual failures.

- **What I would improve next:**
  - Add Excel and CRM-compatible exports.
  - Introduce asynchronous processing and webhook ingestion.
  - Improve handling of large documents and OCR errors.
  - Expand product terminology and specification matching.
  - Evaluate stronger AI models and compare their accuracy, latency, and cost.
  - Build a simple interface where sales representatives can review extracted RFQs and correct uncertain results.

My priority would be to improve the system incrementally rather than introduce unnecessary complexity. The existing implementation establishes the core extraction workflow, while production deployment would require additional infrastructure, reliability, and business-facing integrations.