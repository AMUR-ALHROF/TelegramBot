"""
Treasure hunting specific functionality and knowledge base
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class TreasureHunterGuide:
    """Treasure hunting guidance and knowledge base"""
    
    def __init__(self):
        self.commands_help = {
            "/start": "Start the bot and get welcome message",
            "/help": "Show this help message",
            "/analyze": "Analyze an uploaded image for treasure hunting signals",
            "/ask": "Ask a treasure hunting question",
            "/signal": "Describe a metal detecting signal for analysis",
            "/tips": "Get general treasure hunting tips",
            "/equipment": "Get equipment recommendations",
            "/legal": "Get legal and ethical guidelines",
            "/safety": "Get safety guidelines for treasure hunting"
        }
    
    def get_welcome_message(self) -> str:
        """Get the welcome message for new users"""
        return """🏴‍☠️ **Welcome to Treasure Hunter Bot!** 🏴‍☠️

I'm your AI-powered treasure hunting assistant, ready to help you with:

🔍 **Image Analysis** - Upload photos of finds, signals, or sites
❓ **Expert Q&A** - Ask any treasure hunting questions
📊 **Signal Analysis** - Describe metal detecting signals for interpretation
💡 **Tips & Guidance** - Get expert advice and recommendations

**Quick Start:**
- Send me photos to analyze with /analyze
- Ask questions with /ask [your question]
- Describe signals with /signal [description]
- Use /help for all commands

Happy hunting! 🎯"""
    
    def get_help_message(self) -> str:
        """Get the help message with all commands"""
        help_text = "🎯 **Treasure Hunter Bot Commands:**\n\n"
        
        for command, description in self.commands_help.items():
            help_text += f"`{command}` - {description}\n"
        
        help_text += "\n💡 **Pro Tips:**\n"
        help_text += "• Upload clear, well-lit photos for best analysis\n"
        help_text += "• Include specific questions with your images\n"
        help_text += "• Always follow local laws and get permissions\n"
        help_text += "• Practice safe and ethical treasure hunting\n"
        
        return help_text
    
    def get_general_tips(self) -> str:
        """Get general treasure hunting tips"""
        return """🎯 **General Treasure Hunting Tips:**

**🔍 Research First:**
• Study historical maps and records
• Research local history and settlements
• Check for old foundations, roads, and structures
• Use online resources and libraries

**⚡ Metal Detecting Best Practices:**
• Start with trashy areas to learn your detector
• Use proper swing technique - slow and steady
• Keep coil close to ground and parallel
• Dig all targets when learning
• Fill in all holes and respect property

**🗺️ Site Selection:**
• Old homesteads and farmhouses
• Historic picnic areas and fairgrounds
• Beaches after storms
• Parks and recreational areas (with permission)
• Ghost towns and abandoned settlements

**🛠️ Essential Equipment:**
• Quality metal detector for your budget
• Sturdy digging tools (Lesche digger recommended)
• Finds pouch or bag
• Knee pads for comfort
• Headphones for better audio
• GPS for marking locations

**📜 Legal & Ethical:**
• Always get permission before detecting
• Follow local laws and regulations
• Report significant historical finds
• Leave sites better than you found them
• Respect private property and "No Trespassing" signs

Remember: The best treasure hunters are patient, persistent, and always learning! 🏆"""
    
    def get_equipment_recommendations(self) -> str:
        """Get equipment recommendations"""
        return """🛠️ **Equipment Recommendations by Experience Level:**

**🔰 Beginner Detectors:**
• Garrett ACE 300 - Great starter with target ID
• Bounty Hunter TK4 - Simple and affordable
• Fisher F22 - Weather resistant with good discrimination
• Nokta Simplex+ - Excellent features for the price

**⚡ Intermediate Detectors:**
• Garrett AT Pro - All-terrain versatility
• Fisher F75 - Fast recovery and deep detection
• XP ORX - Wireless and customizable
• Minelab Vanquish 540 - Multi-frequency technology

**🏆 Advanced Detectors:**
• Minelab Equinox 800 - Multi-frequency excellence
• XP Deus - Wireless and highly customizable
• Garrett ATX - Extreme depth for serious hunters
• Minelab CTX 3030 - Top-tier features and performance

**🔧 Essential Accessories:**
• **Digging Tools:** Lesche digger, Predator Tools
• **Headphones:** Koss UR30, detector-specific wireless
• **Finds Storage:** Belt pouch, finds bag with compartments
• **Comfort:** Knee pads, armrest for detector
• **Maintenance:** Cleaning brushes, coil covers

**📱 Useful Apps:**
• iDetecting - Log finds and research
• Metal Detecting Map - Mark locations
• Tide charts for beach hunting
• Historical map overlays

**💰 Budget Tips:**
• Buy quality used equipment
• Start with basic accessories
• Upgrade gradually as you learn
• Join local clubs for group purchases

**🔋 Power Management:**
• Always carry spare batteries
• Consider rechargeable battery packs
• Turn off when not actively hunting
• Use low-power modes when available

Remember: The best detector is the one you learn to use properly! 🎯"""
    
    def get_legal_guidelines(self) -> str:
        """Get legal and ethical guidelines"""
        return """📜 **Legal & Ethical Treasure Hunting Guidelines:**

**🏛️ Legal Requirements:**
• **Private Property:** Always get written permission
• **Public Lands:** Check local regulations and permits
• **Federal Lands:** Generally prohibited without permits
• **State Parks:** Rules vary by state - check first
• **Archaeological Sites:** Strictly protected - stay away

**📋 Permission Best Practices:**
• Approach landowners respectfully
• Explain your hobby and show examples
• Offer to share interesting finds
• Provide insurance information if requested
• Always honor their conditions and restrictions

**🏛️ Historical Preservation:**
• Report significant archaeological finds
• Don't disturb known historical sites
• Photograph finds in context before removal
• Research and document your discoveries
• Consider donating important historical items

**🌍 Environmental Responsibility:**
• Fill in all holes completely
• Pack out all trash you find
• Don't damage vegetation or structures
• Respect wildlife and habitats
• Leave sites cleaner than you found them

**⚖️ Legal Considerations by Location:**
• **Beaches:** Check tide lines and local ordinances
• **Schools:** Usually require district permission
• **Churches:** Get permission from administration
• **Cemeteries:** Generally off-limits everywhere
• **Military Bases:** Absolutely prohibited

**🔍 Research Resources:**
• Local metal detecting clubs
• County courthouse records
• State archaeological departments
• Landowner associations
• Online detecting forums

**🚫 What NOT to Do:**
• Never hunt without permission on private land
• Don't ignore "No Trespassing" signs
• Avoid known archaeological sites
• Don't sell artifacts without research
• Never damage property while digging

**✅ Best Practices:**
• Keep detailed records of finds and locations
• Build good relationships with landowners
• Share knowledge with the detecting community
• Follow the "Treasure Hunter's Code of Ethics"
• Be an ambassador for the hobby

Remember: Ethical hunters preserve the hobby for future generations! 🏆"""
    
    def get_safety_guidelines(self) -> str:
        """Get safety guidelines"""
        return """🛡️ **Treasure Hunting Safety Guidelines:**

**⚠️ Personal Safety:**
• Never hunt alone in remote areas
• Tell someone your hunting plans and location
• Carry a charged cell phone and emergency whistle
• Bring first aid supplies and plenty of water
• Know your physical limits and take breaks

**🌡️ Weather Awareness:**
• Check weather conditions before heading out
• Avoid hunting during storms or severe weather
• Be aware of temperature extremes
• Protect yourself from sun exposure
• Know signs of heat exhaustion and hypothermia

**🏞️ Environmental Hazards:**
• Watch for unstable ground and erosion
• Be aware of wildlife in the area
• Avoid hunting near cliffs or steep embankments
• Check for poison ivy, oak, or other harmful plants
• Be cautious around old wells or structures

**🔧 Equipment Safety:**
• Inspect equipment before each use
• Keep tools sharp and in good condition
• Use proper lifting techniques when digging
• Wear appropriate clothing and footwear
• Consider knee pads and back support

**🏥 Medical Preparedness:**
• Carry a basic first aid kit
• Know how to treat cuts and puncture wounds
• Be prepared for insect bites and stings
• Have emergency contact information readily available
• Consider taking a wilderness first aid course

**🚗 Transportation Safety:**
• Keep vehicles locked with valuables hidden
• Park in safe, legal locations
• Have emergency car supplies (jumper cables, tire repair)
• Keep gas tank at least half full
• Leave a copy of your itinerary with someone

**💡 Common Sense Precautions:**
• Trust your instincts about people and situations
• Don't display valuable finds in public
• Vary your hunting locations and times
• Be discrete about successful hunting spots
• Respect other people's space and activities

**🚨 Emergency Procedures:**
• Know local emergency numbers
• Have GPS coordinates of your location
• Carry emergency signaling devices
• Know the location of nearest hospital
• Have emergency cash and identification

**🏠 At-Home Safety:**
• Secure your finds and equipment
• Don't discuss valuable finds on social media
• Consider insurance for expensive equipment
• Store chemicals and solvents safely
• Keep good records for insurance purposes

**🤝 Group Hunting Safety:**
• Establish communication protocols
• Stay within sight or radio contact
• Have a designated meeting point
• Share emergency contact information
• Look out for each other's safety

Remember: No find is worth your safety or well-being! 🛡️"""
    
    def analyze_common_finds(self, find_description: str) -> str:
        """Analyze and provide information about common finds"""
        find_lower = find_description.lower()
        
        if any(word in find_lower for word in ['coin', 'penny', 'nickel', 'dime', 'quarter']):
            return """🪙 **Coin Find Analysis:**
            
Coins are the most common and rewarding finds for treasure hunters!

**Identification Tips:**
• Check dates and mint marks
• Look for silver content (pre-1965 US coins)
• Note condition and wear patterns
• Research rare dates and varieties

**Cleaning Guidelines:**
• Never clean valuable or old coins
• Use distilled water for basic cleaning
• Soft brush for removing dirt only
• Consider professional cleaning for valuable pieces

**Value Assessment:**
• Check current precious metal prices
• Use coin value guides and apps
• Consider rarity, condition, and demand
• Get professional appraisal for valuable coins"""
        
        elif any(word in find_lower for word in ['jewelry', 'ring', 'necklace', 'bracelet']):
            return """💍 **Jewelry Find Analysis:**
            
Jewelry finds can range from costume pieces to valuable treasures!

**Initial Assessment:**
• Look for hallmarks (14k, 18k, 925, etc.)
• Check for maker's marks or signatures
• Note gemstones and their settings
• Assess overall condition and craftsmanship

**Metal Testing:**
• Use acid test kits for precious metals
• Check for magnetic properties
• Look for tarnishing patterns
• Consider professional testing for valuable pieces

**Gemstone Evaluation:**
• Real vs. synthetic identification
• Check clarity, color, and cut quality
• Look for natural inclusions
• Consider professional appraisal

**Restoration Tips:**
• Clean gently with appropriate solutions
• Don't over-polish or damage patina
• Consider professional restoration for valuable pieces
• Document before and after condition"""
        
        elif any(word in find_lower for word in ['button', 'buckle', 'relic', 'artifact']):
            return """🏺 **Historical Artifact Analysis:**
            
Historical relics provide fascinating glimpses into the past!

**Age Determination:**
• Research manufacturing techniques and materials
• Look for maker's marks or patent dates
• Study style and design characteristics
• Cross-reference with historical records

**Historical Context:**
• Research the site's history and timeline
• Connect finds to known historical events
• Study period clothing, military, or household items
• Document the discovery location carefully

**Preservation:**
• Clean carefully with appropriate methods
• Prevent further corrosion or deterioration
• Store in stable temperature and humidity
• Consider professional conservation for important pieces

**Research Resources:**
• Historical societies and museums
• Online databases and forums
• Military and clothing history books
• Archaeological reports for the area"""
        
        else:
            return """🔍 **General Find Analysis:**
            
Every find tells a story and adds to your treasure hunting experience!

**Documentation:**
• Photograph finds in their discovery context
• Record GPS coordinates and depth
• Note detector settings and signal characteristics
• Keep a detailed hunting log

**Research Process:**
• Use online identification resources
• Consult with experienced hunters
• Visit local museums or historical societies
• Join online forums for expert opinions

**Preservation:**
• Clean appropriately for the material type
• Store in protective containers
• Control temperature and humidity
• Document any restoration work

**Value Assessment:**
• Research similar items and sales
• Consider historical significance
• Assess rarity and condition
• Get professional opinions when needed"""
