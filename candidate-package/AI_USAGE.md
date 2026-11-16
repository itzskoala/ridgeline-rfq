# AI Usage

- **Tool:** ChatGPT Free, accessed through the browser. All code was manually copied between ChatGPT and VS Code.
- **Model selection:** Intentionally used a free-tier model to maintain control over implementation decisions rather than relying on AI to generate entire solutions.
- **Coding principles:** Consistently instructed the model to follow SOLID, YAGNI, and KISS. Prioritized simple, maintainable implementations over unnecessary abstractions and overengineering.
- **Instruction files:** None used.
- **Subagents / skills / MCP servers:** None used.

## How I Worked

- **Planning:** Started by designing the project architecture myself using paper diagrams, pseudocode, and existing logic to map out the system before using AI.
- **Implementation:** Built the initial codebase and established the architecture myself. Used ChatGPT to help implement individual functions, answer technical questions, generate test cases, and explore hypothetical solutions.
- **Development process:** Worked from paper diagrams to pseudocode, then translated those ideas into code. My early commits contain rough comments and pseudocode that reflect my initial thought process.
- **Testing:** Ran implementations against my existing answer key and test cases to evaluate correctness. Manually inspected the code and output, then returned to ChatGPT to refine incorrect implementations.
- **Code review:** Frequently asked ChatGPT to simplify implementations, critique its own suggestions, consider newer packages, and explore alternative approaches.
- **Decision-making:** Treated AI suggestions as alternatives rather than instructions. I retained control over the architecture, implementation choices, and final code.

## Three Moments

### 1. The AI Was Wrong, and How I Caught It

- ChatGPT repeatedly suggested that its proposed `ai_extractor.py` implementations were the best approach.
- Rather than trusting those suggestions, I evaluated each implementation against my existing answer key and test cases.
- I manually inspected the code and extraction results after running each implementation.
- When results did not meet my baseline criteria, I returned to ChatGPT to identify issues and refine the implementation.
- **Evidence:** `b11a092` (AI layer). Session: ChatGPT browser conversation.

### 2. I Overruled It, and Why

- While developing `ai_extractor.py`, ChatGPT proposed alternative implementations that did not always align with my original design.
- I returned to the architecture and pseudocode I had written before using AI.
- I explored multiple implementations rather than accepting the first generated solution.
- I prioritized my original design principles, keeping the implementation simple and avoiding unnecessary complexity.
- **Evidence:** `b11a092` (AI layer). Session: ChatGPT browser conversation.

### 3. It Saved Me Real Time

- ChatGPT saved the most time by physically writing code and translating my pseudocode and existing logic into working Python functions.
- It helped with implementation, boilerplate, package recommendations, test cases, and exploring different approaches.
- However, generated code still required review and refinement. I frequently asked the model to simplify its code, critique its implementation, and consider newer libraries or packages.
- This allowed me to spend more time on architecture, testing, reviewing outputs, and making engineering decisions.
- **Evidence:** `e91f855` (initial ingestion logic) and `38f2716` (ingestion and reply connections). Session: ChatGPT browser conversations.