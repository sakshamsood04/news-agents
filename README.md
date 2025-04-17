# Multi-Agent News Analysis System

## Overview

The **Multi-Agent News Analysis System** is a Python-based tool designed to provide unbiased and balanced summaries of news articles from multiple sources. Using browser automation, multi-agent workflows, and language models, the system extracts content from diverse news outlets and synthesizes a centrist summary for any given topic.

### Key Features
- **Multi-Source Analysis**: Extracts articles from major news outlets with varying political biases:
  - Right-wing: Fox News
  - Left-wing: CNN
  - Neutral/International: Reuters, BBC, Al Jazeera, Associated Press
- **Centrist Summarization**: Creates a balanced summary by analyzing key facts and differences in reporting styles.
- **Automated Workflow**: Utilizes browser automation to search Google and extract relevant articles directly from source websites.
- **Scalable Design**: Processes multiple sources concurrently using asynchronous tasks.

## Quick Start Instructions

- Create a `.env` file in your project directory containing your OpenAI API key:
  `OPENAI_API_KEY=your_openai_api_key_here`

- In your terminal, run:
  `python news.py`

- When prompted, enter the name of the news story you want to analyze.

---

## How It Works

### Workflow
1. **Input Query**: The user provides a topic or news story to analyze.
2. **Source Search**:
   - Performs Google searches for each news outlet using site-specific queries.
   - Extracts article titles, URLs, and content while avoiding irrelevant sections like ads or comments.
3. **Content Extraction**:
   - Articles are parsed and cleaned for structured analysis.
   - Metadata such as source, title, content, and URL are saved for each article.
4. **Centrist Summary Generation**:
   - A GPT-based language model synthesizes the extracted content into an unbiased summary.
   - Highlights differences in reporting styles across sources.
5. **Output**:
   - Saves the centrist summary to `summary.txt`.

---

## Technologies Used

### Programming Language
- **Python**

### Core Libraries
- **LangChain OpenAI**: For natural language processing and summarization using GPT-based models.
- **Browser Automation Framework**:
  - `browser_use` library for controlling browser actions.
  - Puppeteer-like functionality for navigating websites and extracting content.

### Data Models
- **Pydantic**: For structured data validation (e.g., `NewsArticle`, `SourceResult`).

### Environment Management
- **dotenv**: For managing API keys and sensitive configurations.
