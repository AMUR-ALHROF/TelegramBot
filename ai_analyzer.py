"""
AI-powered analysis module using OpenAI GPT-4o
"""

import json
import os
import logging
from typing import Dict, Optional, Any
from openai import OpenAI

logger = logging.getLogger(__name__)

class AIAnalyzer:
    """AI analyzer for treasure hunting images and questions"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the AI analyzer with OpenAI client"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = OpenAI(api_key=self.api_key)
        
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.model = "gpt-4o"
    
    async def analyze_treasure_image(self, base64_image: str, user_question: str = "") -> Dict[str, Any]:
        """Analyze an image for treasure hunting signals and patterns"""
        try:
            system_prompt = """You are an expert treasure hunter and metal detecting specialist with decades of experience. 
            Analyze images for potential treasure hunting signals, archaeological indicators, and valuable finds.
            
            Focus on:
            - Metal detecting signals and patterns
            - Soil composition and color changes
            - Potential archaeological features
            - Historical artifacts identification
            - Ground disturbances or anomalies
            - Valuable items or materials
            - Dating and historical context
            - Safety considerations
            
            Provide detailed, expert analysis with practical advice."""
            
            user_content = [
                {
                    "type": "text",
                    "text": f"""Analyze this treasure hunting image in detail. 
                    Look for any signals, patterns, artifacts, or indicators that would be valuable to treasure hunters.
                    
                    {f'User specific question: {user_question}' if user_question else ''}
                    
                    Provide your analysis in a structured format covering:
                    1. Initial observations
                    2. Potential finds or signals
                    3. Historical/archaeological context
                    4. Recommendations for further investigation
                    5. Safety and legal considerations"""
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                }
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            analysis = response.choices[0].message.content
            
            return {
                "success": True,
                "analysis": analysis,
                "type": "image_analysis"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing treasure image: {e}")
            return {
                "success": False,
                "error": f"Failed to analyze image: {str(e)}",
                "type": "error"
            }
    
    async def answer_treasure_question(self, question: str, context: str = "") -> Dict[str, Any]:
        """Answer treasure hunting related questions"""
        try:
            system_prompt = """You are an expert treasure hunter, metal detecting specialist, and archaeologist.
            Provide detailed, accurate, and helpful answers to treasure hunting questions.
            
            Your expertise includes:
            - Metal detecting techniques and equipment
            - Historical research and site analysis
            - Artifact identification and dating
            - Legal and ethical treasure hunting
            - Safety protocols and best practices
            - Equipment recommendations
            - Site permissions and regulations
            
            Always emphasize legal and ethical practices, proper permissions, and respect for historical sites."""
            
            user_prompt = f"""Question: {question}
            
            {f'Additional context: {context}' if context else ''}
            
            Please provide a comprehensive answer with practical advice and recommendations."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            
            return {
                "success": True,
                "answer": answer,
                "type": "question_answer"
            }
            
        except Exception as e:
            logger.error(f"Error answering treasure question: {e}")
            return {
                "success": False,
                "error": f"Failed to answer question: {str(e)}",
                "type": "error"
            }
    
    async def analyze_signal_pattern(self, description: str) -> Dict[str, Any]:
        """Analyze described metal detecting signals for pattern recognition"""
        try:
            system_prompt = """You are a master metal detecting specialist with expertise in signal interpretation.
            Analyze signal descriptions and provide expert guidance on what they might indicate.
            
            Consider:
            - Signal strength and consistency
            - Target depth indicators
            - Discrimination patterns
            - Ground conditions
            - Potential target types
            - False positive indicators
            - Digging recommendations"""
            
            user_prompt = f"""Signal description: {description}
            
            Please analyze this metal detecting signal and provide:
            1. Likely target identification
            2. Confidence level assessment
            3. Recommended digging approach
            4. Potential challenges or considerations
            5. Equipment settings suggestions"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=600,
                temperature=0.7
            )
            
            analysis = response.choices[0].message.content
            
            return {
                "success": True,
                "analysis": analysis,
                "type": "signal_analysis"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing signal pattern: {e}")
            return {
                "success": False,
                "error": f"Failed to analyze signal: {str(e)}",
                "type": "error"
            }
