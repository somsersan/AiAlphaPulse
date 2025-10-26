"""News analyzer for generating detailed information via LLM"""
import json
import os
from typing import Dict
from ..llm.openrouter_client import OpenRouterClient


class NewsAnalyzer:
    """Generates detailed analytics for news"""
    
    def __init__(self, api_key: str = None, model: str = None):
        # Use more powerful model for detailed analysis
        # LLM_ANALYSIS_MODEL - for detailed analysis (default Claude 3.5 Sonnet)
        # LLM_MODEL - for quick hotness evaluation
        self.analysis_model = model or os.getenv("LLM_ANALYSIS_MODEL", "anthropic/claude-3.5-sonnet")
        self.llm_client = OpenRouterClient(api_key=api_key, model=self.analysis_model)
    
    def generate_full_analysis(self, news: Dict) -> Dict:
        """
        Generates full news analysis in analytical card format
        
        Args:
            news: dict with headline, content, tickers, hotness, urls, published_at, source
            
        Returns:
            {
                'analysis_text': str - ready card in Markdown format
            }
        """
        
        headline = news.get('headline', '')
        content = news.get('content', '')
        tickers = news.get('tickers', [])
        hotness = news.get('hotness', 0)
        urls = news.get('urls', [])
        published_at = news.get('published_at', '')
        source = news.get('source', 'Unknown source')
        
        # Create prompt for analytical card generation
        prompt = self._create_analysis_card_prompt(headline, content, tickers, hotness, urls, published_at, source)
        
        headers = {
            "Authorization": f"Bearer {self.llm_client.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.analysis_model,  # Use powerful model
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,  # Lower temperature for precise analysis
            "max_tokens": 1500  # More tokens for detailed analysis
        }
        
        try:
            import requests
            response = requests.post(
                self.llm_client.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                return self._get_fallback_analysis(hotness)
            
            result = response.json()
            content = result['choices'][0]['message']['content']

            # Normalize model response: remove markdown fences and extract JSON
            import re
            raw_content = content or ""
            if "```json" in raw_content:
                try:
                    content = raw_content.split("```json", 1)[1].split("```", 1)[0]
                except Exception:
                    content = raw_content
            elif "```" in raw_content:
                try:
                    content = raw_content.split("```", 1)[1].split("```", 1)[0]
                except Exception:
                    content = raw_content
            else:
                content = raw_content

            # Extract JSON substring by outer curly braces
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)

            # Remove problematic control characters, keeping line breaks
            def _sanitize(s: str) -> str:
                if not isinstance(s, str):
                    return s
                # Remove BOM and null bytes/vertical tabs/form feeds
                s = s.replace('\ufeff', '')
                s = s.replace('\x00', '').replace('\x0b', ' ').replace('\x0c', ' ')
                return s

            content = _sanitize(content)

            # Check that valid content remains after all processing
            if not content or not content.strip():
                print(f"⚠️ Analysis generation error: empty response from LLM")
                return self._get_fallback_analysis(hotness, urls, published_at, source)

            # Parse JSON, allowing unescaped control characters inside strings
            analysis = json.loads(content.strip(), strict=False)
            return analysis
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Analysis generation error: invalid JSON - {e}")
            print(f"Received response: {content if 'content' in locals() else 'N/A'}")
            return self._get_fallback_analysis(hotness, urls, published_at, source)
        except Exception as e:
            print(f"⚠️ Analysis generation error: {e}")
            return self._get_fallback_analysis(hotness, urls, published_at, source)
    
    def _create_analysis_card_prompt(self, headline: str, content: str, tickers: list, hotness: float, urls: list, published_at: str, source: str) -> str:
        """Prompt for generating news analytical card"""
        tickers_str = ', '.join(tickers) if tickers else '—'
        url_str = urls[0] if urls else 'no link'
        
        # Determine language based on headline
        is_russian = any(ord(c) >= 0x0400 and ord(c) <= 0x04FF for c in headline)
        lang_instruction = "на русском языке" if is_russian else "in English"
        
        return f"""You are a financial news analytics agent for the AI ALPHA PULSE Telegram bot. Your task is to create a compact, explainable analytical card {lang_instruction}.

INPUT DATA:
Headline: {headline}
Text: {content[:2000]}
Tickers: {tickers_str}
Source: {source}
Publication time: {published_at}
URL: {url_str}
Hotness score: {hotness:.2f}

OUTPUT REQUIREMENTS:
Create an analytical card in Markdown format (Telegram-compatible). Card language: {lang_instruction}.

MANDATORY FIELDS (strictly in this order):

1. TL;DR (20-30 words): News essence and its impact on markets/assets
2. Key facts (2-4 points): Specific facts from text, no speculation
3. Affected assets: Comma-separated ticker list or "—"
4. Sentiment score: Number from -1 to 1 and brief explanation (why positive/negative/neutral)
5. News score: Number from 0 to 1 and main drivers (sentiment / mentions / authority)
6. Recommendation: "Monitor" / "Bullish (consider buy)" / "Bearish (consider sell)" / "No action" + 1-2 sentence explanation
7. Confidence: "Low" / "Medium" / "High" + justification (why this confidence level)

STYLE:
- Brief, neutral, business-like. Maximum 700 characters
- Use phrases: "consider", "monitor", "may indicate" (don't give direct financial advice)
- If data is insufficient — indicate this in Confidence and TL;DR
- Don't make up statistics if they're not in the text
- Use emojis where appropriate

Reply ONLY in JSON format:
{{
    "analysis_text": "🔎 *TL;DR:* ...\\n\\n📌 *Key facts:*\\n• Fact 1\\n• Fact 2\\n• Fact 3\\n\\n📈 *Affected assets:* ...\\n💡 *Sentiment:* ... — ...\\n⭐ *News score:* ... — drivers: ...\\n\\n🧭 *Recommendation:* ... — ...\\n🔒 *Confidence:* ... — ...\\n\\n🔗 {url_str}"
}}

IMPORTANT: All card text must be in one line analysis_text with escaped line breaks (\\n). Use Markdown formatting (*bold text*) for field headers."""
    
    def _get_fallback_analysis(self, hotness: float, urls: list, published_at: str, source: str) -> Dict:
        """Fallback analysis on LLM error"""
        url_str = urls[0] if urls else 'no link'
        
        fallback_text = f"""🔎 *TL;DR:* Analysis temporarily unavailable — LLM processing error.

📌 *Key facts:*
• News requires manual analysis
• Automatic processing failed

📈 *Affected assets:* —
💡 *Sentiment:* 0.0 — not determined
⭐ *News score:* {hotness:.2f} — baseline hotness score

🧭 *Recommendation:* Monitor — additional analysis required
🔒 *Confidence:* Low — automatic analysis unavailable

🔗 {url_str}"""
        
        return {
            'analysis_text': fallback_text
        }

