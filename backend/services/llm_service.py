import os
from groq import Groq
from typing import List, Optional
import json
from schemas.models import Paper, PaperInsight

from tavily import TavilyClient

class LLMService:
    def __init__(self, api_key: str, tavily_key: Optional[str] = None):
        self.client = Groq(api_key=api_key)
        self.tavily = TavilyClient(api_key=tavily_key) if tavily_key else None
        self.model = "llama-3.3-70b-versatile"

    async def generate_insights(self, paper: Paper) -> PaperInsight:
        prompt = f"""
        Analyze the following research paper abstract and provide key insights:
        Title: {paper.title}
        Abstract: {paper.abstract}

        Return the response in the following JSON format:
        {{
            "summary": "Concise 2-3 sentence summary",
            "key_technologies": ["tech1", "tech2"],
            "research_gaps": ["gap1", "gap2"],
            "multimodal_insights": "Optional note on potential figures/charts if mentioned"
        }}
        """
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a specialized AI assistant in Bioinformatics and AI research. Always respond in valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.model,
                response_format={"type": "json_object"}
            )
            data = json.loads(chat_completion.choices[0].message.content)
            return PaperInsight(**data)
        except Exception as e:
            print(f"Error generating insights for {paper.title}: {e}")
            return PaperInsight(
                summary="Insight generation failed. " + paper.abstract[:150] + "...",
                key_technologies=["Manual Review Required"],
                research_gaps=["Check paper for details"]
            )

    async def answer_paper_question(self, paper_context: dict, question: str) -> str:
        """Answer a specific question about a paper using its abstract and insights as context."""
        prompt = f"""
        CONTEXT:
        Paper Title: {paper_context['title']}
        Abstract: {paper_context['abstract']}
        Key Insights: {paper_context['insights']}

        USER QUESTION:
        {question}

        Provide a concise, expert answer based on the context provided. If the answer isn't in the context, use your general knowledge but specify it's based on general expertise.
        """
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a helpful research assistant."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Chat error: {e}"

    async def perform_cross_paper_analysis(self, papers: List[Paper]) -> str:
        """Analyze a collection of papers to find overarching research gaps."""
        paper_summaries = "\n".join([f"- {p.title}: {p.insights.summary if p.insights else p.abstract[:100]}" for p in papers])
        prompt = f"""
        You are looking at a collection of the latest research papers in AI and Bioinformatics:
        {paper_summaries}

        Identify the 'Missing Link':
        1. What is the biggest technology gap across these works?
        2. Is there a common challenge they all face but haven't solved?
        3. Provide 3 specific 'Innovation Opportunities' for a researcher.
        
        Respond in a structured, professional tone.
        """
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Gap analysis unavailable: {e}"

    async def search_web_innovation(self, query: str) -> str:
        """Use Tavily to get real-time research results from the web."""
        if not self.tavily:
            return "Tavily API key not configured. Please add TAVILY_API_KEY to environment."

        try:
            # Search for the latest 24h innovation trends
            search_result = self.tavily.search(
                query=f"latest 24h innovation trends in {query}",
                search_depth="advanced",
                max_results=5
            )
            
            # Use LLM to synthesize the search results into a clean summary
            context = json.dumps(search_result['results'])
            prompt = f"""
            Based on these search results, provide a concise synthesis of the latest innovations in {query}:
            {context}

            Focus on specific breakthroughs, new papers, or technology releases from the last 24-48 hours.
            """
            
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"Tavily search error: {e}")
            return f"Error performing live research: {e}"

    async def analyze_figure(self, paper_title: str, image_path: str) -> str:
        # Multimodal analysis placeholder
        prompt = f"Analyze this figure from the paper '{paper_title}' and explain its significance in the context of AI or Bioinformatics."
        # This would pass the image bytes to Gemini
        return "Insight about the chart/figure would be generated here."
