"""
Multi-Agent News Analysis System

This program uses browser-use to search multiple news sources for a given topic,
extracts article content, and creates a centrist summary of the information.

Sources include: Fox News (right-wing), CNN (left-wing), Reuters, BBC, 
Al Jazeera, and Associated Press (international)
"""

import asyncio
from typing import List, Dict, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from browser_use import Agent, Browser, Controller, ActionResult

load_dotenv()


class NewsArticle(BaseModel):
    source: str
    title: str
    content: str
    url: str

class SourceResult(BaseModel):
    source: str
    articles: List[NewsArticle]
    error: Optional[str] = None

controller = Controller()

@controller.action('Save article information')
def save_article(title: str, content: str, url: str, source: str) -> str:
    """Save information about a news article."""
    cleaned_content = " ".join(content.split())
    
    article = NewsArticle(
        source=source,
        title=title,
        content=cleaned_content,
        url=url
    )
    return ActionResult(extracted_content=article.json())

@controller.action('Google search')
async def google_search(query: str, browser: Browser) -> str:
    """Perform a Google search and return the search results page."""
    page = browser.get_current_page()
    
    await page.goto("https://www.google.com/")
    
    await page.wait_for_selector('input[name="q"]')
    await page.fill('input[name="q"]', query)
    
    await page.press('input[name="q"]', 'Enter')
    
    await page.wait_for_selector('#search')
    
    return ActionResult(extracted_content="Google search completed for: " + query)

async def search_news_source(source_name: str, search_query: str, search_url: str, llm) -> SourceResult:
    """
    Search for articles from a specific news source related to the query using Google.
    """
    browser = None
    try:
        browser = Browser()
        
        task = f"""
        You are a news research agent for {source_name}. Your task is to:
        
        1. Go to Google.com
        2. Search for: "{search_query} {source_name} site:{search_url.replace('https://www.', '')}"
        3. Look for search results that are from {source_name}'s website ({search_url})
        4. Open the most relevant and recent article about this topic from {source_name}
        5. For each article you find:
           - Read and extract the complete article content
           - Note the article title and URL
           - Use the "Save article information" action to save this information with source="{source_name}"
        6. Try to find 1-2 more articles on the same topic from {source_name} if available (go back to Google results)
        
        Be thorough in extracting the complete article text, but avoid comments sections and advertisements.
        Make sure the articles you open are actually from {source_name}'s official website.
        If you cannot find any relevant articles, explain why and stop.
        """
        
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            controller=controller
        )
        
        try:
            history = await asyncio.wait_for(
                agent.run(max_steps=30),
                timeout=300  
            )
            
            articles = []
            for content in history.extracted_content():
                if content:
                    try:
                        article = NewsArticle.model_validate_json(content)
                        if article.source != source_name:
                            article.source = source_name
                        articles.append(article)
                    except Exception as e:
                        print(f"Error parsing article from {source_name}: {e}")
            
        except asyncio.TimeoutError:
            print(f"Timeout searching {source_name}")
            return SourceResult(
                source=source_name,
                articles=[],
                error="Timeout occurred while searching"
            )
        
        return SourceResult(
            source=source_name,
            articles=articles
        )
    
    except Exception as e:
        print(f"Error searching {source_name}: {str(e)}")
        return SourceResult(
            source=source_name,
            articles=[],
            error=str(e)
        )
    
    finally:
        if browser:
            try:
                await browser.close()
            except Exception as e:
                print(f"Error closing browser for {source_name}: {e}")

async def create_summary(all_results: List[SourceResult], search_query: str, llm) -> str:
    """
    Create a centrist summary of all the articles.
    """
    articles_summary = ""
    sources_with_articles = 0
    sources_list = []
    
    for result in all_results:
        if result.articles:
            sources_with_articles += 1
            sources_list.append(result.source)
            articles_summary += f"\n\n### {result.source} ARTICLES ###\n"
            for idx, article in enumerate(result.articles):
                articles_summary += f"\n--- Article {idx+1} ---\n"
                articles_summary += f"Title: {article.title}\n"
                articles_summary += f"URL: {article.url}\n"
                content = article.content[:5000] + "..." if len(article.content) > 5000 else article.content
                articles_summary += f"Content:\n{content}\n"
    
    if sources_with_articles == 0:
        return "No articles were found across any of the news sources. Unable to create a summary."
    
    task = f"""
    You are an objective news analyst. Your task is to create a centrist, balanced summary of news articles about "{search_query}" from various sources.
    
    Here are the articles from different news organizations (which may have different political biases or perspectives):
    
    {articles_summary}
    
    Please analyze these articles and create a comprehensive but concise summary (500-1000 words) that:
    
    1. Presents the key facts that appear across multiple sources
    2. Identifies any significant differences in how the story is reported by different outlets
    3. Avoids adopting any particular political slant or bias
    4. Focuses on verifiable information rather than opinion or commentary
    5. Presents a balanced view that readers of any political leaning would find fair
    
    Your summary should be well-structured with clear paragraphs and organized by the main aspects of the story.
    Include a section at the end that briefly notes any significant differences in coverage between sources.
    
    Format your summary as follows:
    
    # Centrist Summary: {search_query}
    
    ## Overview
    [1-2 paragraphs providing a high-level overview of the story]
    
    ## Key Facts
    [The main facts of the story that appear across multiple sources]
    
    ## Analysis
    [Deeper analysis of the situation, including context and implications]
    
    ## Different Perspectives
    [Brief notes on how different sources covered the story differently, if applicable]
    
    ## Sources
    [List of sources used for this summary]
    """
    
    browser = Browser()
    try:
        summarizer = Agent(
            task=task,
            llm=llm,
            browser=browser
        )
        

        history = await summarizer.run(max_steps=10)

        summary = history.final_result() or "No summary could be generated."
        
        return summary
    finally:
        await browser.close()

async def process_news_sources_in_batches(news_sources, search_query, llm, batch_size=2):
    """Process news sources in batches to limit concurrent browser instances."""
    all_results = []
    
    for i in range(0, len(news_sources), batch_size):
        batch = news_sources[i:i+batch_size]
        
        print(f"Processing batch {i//batch_size + 1}: {', '.join([source['name'] for source in batch])}")
        
        tasks = []
        for source in batch:
            print(f"Searching for '{search_query}' articles from {source['name']}...")
            tasks.append(search_news_source(
                source["name"], 
                search_query, 
                source["url"], 
                llm
            ))
        
        batch_results = await asyncio.gather(*tasks)
        all_results.extend(batch_results)
        
        print(f"Completed batch {i//batch_size + 1}")
        
        if i + batch_size < len(news_sources):
            await asyncio.sleep(5)
    
    return all_results

async def main():
    search_query = input("Enter the name of a news story to search for: ")
    
    llm = ChatOpenAI(model="gpt-4o")
    
    news_sources = [
        {"name": "Fox News", "url": "foxnews.com"},
        {"name": "CNN", "url": "cnn.com"},
        {"name": "Reuters", "url": "reuters.com"},
        {"name": "BBC", "url": "bbc.com"},
        {"name": "Al Jazeera", "url": "aljazeera.com"},
        {"name": "Associated Press", "url": "apnews.com"}
    ]
    
    print(f"Starting multi-agent news analysis for: '{search_query}'")
    print(f"This will search {len(news_sources)} different news sources.")
    print("Please be patient, this process may take several minutes...\n")
    
    all_results = await process_news_sources_in_batches(news_sources, search_query, llm, batch_size=2)
    
    total_articles = 0
    print("\nSearch results summary:")
    print("------------------------")
    for result in all_results:
        article_count = len(result.articles)
        total_articles += article_count
        if article_count > 0:
            print(f"✓ Found {article_count} article(s) from {result.source}")
        else:
            error_msg = f": {result.error}" if result.error else ""
            print(f"✗ No articles found from {result.source}{error_msg}")
    
    if total_articles == 0:
        print(f"\nNo articles found for '{search_query}' from any source.")
        with open("summary.txt", "w", encoding="utf-8") as f:
            f.write(f"No articles found for '{search_query}' from any news source.")
        print(f"A note has been saved to summary.txt")
        return "No articles found."
    
    print(f"\nFound {total_articles} total articles. Creating a centrist summary...")
    summary = await create_summary(all_results, search_query, llm)
    
    with open("summary.txt", "w", encoding="utf-8") as f:
        f.write(summary)
    
    print(f"\nSummary saved to summary.txt")
    print("Process complete!")
    
    return summary

if __name__ == "__main__":
    asyncio.run(main())