import os
from groq import Groq
from tavily import TavilyClient
import google.generativeai as genai
from typing import List, Optional
import json
from schemas.models import Paper, PaperInsight

class LLMService:
    def __init__(self, api_key: str, tavily_key: Optional[str] = None, gemini_key: Optional[str] = None):
        self.client = Groq(api_key=api_key)
        self.tavily = TavilyClient(api_key=tavily_key) if tavily_key else None
        
        # New: Gemini Fallback
        self.gemini_key = gemini_key
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.gemini_model = None
            
        # Use a model with higher rate limits for better stability
        self.model = "llama-3.1-8b-instant" 

    async def _call_with_fallback(self, prompt: str, system_prompt: str = "You are a specialized AI assistant in Bioinformatics and AI research.", force_json: bool = False):
        """Internal helper to call Groq with a Gemini fallback on 429/failure."""
        try:
            # Try Groq first
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
            
            kwargs = {
                "messages": messages,
                "model": self.model,
            }
            if force_json:
                kwargs["response_format"] = {"type": "json_object"}
                
            chat_completion = self.client.chat.completions.create(**kwargs)
            return chat_completion.choices[0].message.content
        except Exception as groq_err:
            print(f"Groq API Error: {groq_err}")
            if self.gemini_model:
                print("Falling back to Gemini...")
                try:
                    gemini_prompt = f"{system_prompt}\n\n{prompt}"
                    response = self.gemini_model.generate_content(gemini_prompt)
                    return response.text
                except Exception as gemi_err:
                    print(f"Gemini Fallback Error: {gemi_err}")
                    raise gemi_err
            else:
                raise groq_err

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
            content = await self._call_with_fallback(
                prompt=prompt, 
                system_prompt="You are a specialized AI assistant in Bioinformatics and AI research. Always respond in valid JSON.",
                force_json=True
            )
            
            # Robust JSON extraction
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            
            # Remove potential common JSON errors from LLMs (like trailing commas)
            content = re.sub(r',\s*\}', '}', content)
            content = re.sub(r',\s*\]', ']', content)
                
            data = json.loads(content)
            return PaperInsight(**data)
        except Exception as e:
            print(f"Error parsing insights for {paper.title}: {e}")
            return PaperInsight(
                summary=f"Insight generation failed. {paper.abstract[:150]}...",
                key_technologies=["Manual Review Required"],
                research_gaps=["Check paper for details"]
            )

    async def answer_paper_question(self, paper_context: dict, question: str) -> str:
        prompt = f"""
        CONTEXT:
        Paper Title: {paper_context['title']}
        Abstract: {paper_context['abstract']}
        Key Insights: {paper_context['insights']}

        USER QUESTION:
        {question}

        Provide a concise, expert answer based on the context provided.
        """
        try:
            return await self._call_with_fallback(prompt, system_prompt="You are a helpful research assistant.")
        except Exception as e:
            return f"Chat error: {e}. (Both primary and fallback AI are currently limited)"

    async def perform_cross_paper_analysis(self, papers: List[Paper]) -> str:
        paper_summaries = "\n".join([f"- {p.title}: {p.insights.summary if p.insights else p.abstract[:100]}" for p in papers])
        prompt = f"""
        You are looking at a collection of the latest research papers in AI and Bioinformatics:
        {paper_summaries}

        Identify the 'Missing Link':
        1. What is the biggest technology gap across these works?
        2. Is there a common challenge they all face but haven't solved?
        3. Provide 3 specific 'Innovation Opportunities' for a researcher.
        """
        try:
            return await self._call_with_fallback(prompt)
        except Exception as e:
            return f"Analysis unavailable: {e}"

    async def search_web_innovation(self, query: str) -> str:
        if not self.tavily:
            return "Tavily API key not configured."

        try:
            search_result = self.tavily.search(query=f"latest 24h innovation trends in {query}", search_depth="advanced", max_results=5)
            context = json.dumps(search_result['results'])
            prompt = f"Based on these results, summarize innovations in {query}:\n{context}"
            return await self._call_with_fallback(prompt)
        except Exception as e:
            return f"Search error: {e}"

    async def analyze_figure(self, paper_title: str, image_path: str) -> str:
        # Gemini can actually do this better if implemented correctly
        return "Visual analysis feature is currently being integrated into the fallback brain."
