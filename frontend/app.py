import streamlit as st
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Set page configuration
st.set_page_config(
    page_title="PQNK Farming Assistant",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - Updated with About page styles
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&family=Playfair+Display:wght@700&display=swap');

html, body, [class*="css"] {
    font-family: 'Montserrat', sans-serif;
}

.sticky-header {
    position: sticky;
    top: 0;
    z-index: 100;
    background: #4a9f4e;
    padding: 15px 0;
    margin-bottom: 20px;
    border-radius: 0 0 16px 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    border-bottom: 3px solid #81c784;
}

.animated-title {
    font-size: 2.5rem !important;
    font-weight: 700 !important;
    text-align: center !important;
    font-family: 'Playfair Display', serif !important;
    color: #ffffff !important;
    margin: 0 !important;
    padding: 10px 0 !important;
    letter-spacing: 1px !important;
    text-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
}

/* Sidebar styling */
.stSidebar {
    background: linear-gradient(to bottom, #e8f5e9, #c8e6c9) !important;
    border-right: 1px solid #a5d6a7;
}

.sidebar-container {
    background-color: white;
    border-radius: 16px;
    padding: 20px;
    margin: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    border: 1px solid #e0e0e0;
}

.sidebar-title {
    color: #1a4d1e;
    font-family: 'Playfair Display', serif;
    text-align: center;
    margin-bottom: 5px;
    font-size: 1.5rem;
}

.sidebar-subtitle {
    color: #2e7d32;
    text-align: center;
    font-size: 14px;
    margin-bottom: 20px;
}

.sidebar-logo {
    text-align: center;
    margin-bottom: 20px;
}

.sidebar-logo img {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    border: 3px solid #81c784;
    padding: 5px;
    background-color: white;
}

.sidebar-tips {
    margin-top: 25px;
    padding-top: 15px;
    border-top: 1px solid #e0e0e0;
}

.sidebar-tips-title {
    font-weight: 600;
    color: #1a4d1e;
    margin-bottom: 10px;
}

.sidebar-tips-list {
    padding-left: 20px;
    color: #2e7d32;
}

.sidebar-tips-list li {
    margin-bottom: 8px;
}

/* Updated Clear Conversation Button with Classy Vibrant Gradient */
.stButton > button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    border-radius: 12px !important;
    padding: 12px !important;
    width: 80% !important;
    border: none !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    margin: 10px auto !important;
    display: block !important;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2) !important;
    font-size: 16px !important;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #764ba2 0%, #667eea 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.3) !important;
    color: white !important;
}

/* About Page Styles */
.about-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 40px 20px;
    border-radius: 16px;
    margin-bottom: 30px;
    text-align: center;
    box-shadow: 0 8px 16px rgba(0,0,0,0.1);
    animation: fadeIn 0.8s ease-out;
}

.about-header h1 {
    font-family: 'Playfair Display', serif;
    font-size: 3rem;
    margin-bottom: 15px;
    text-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.about-header p {
    font-size: 1.2rem;
    max-width: 800px;
    margin: 0 auto;
    opacity: 0.9;
}

.about-section {
    background: white;
    border-radius: 16px;
    padding: 30px;
    margin-bottom: 30px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    border-left: 5px solid #667eea;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    animation: slideUp 0.6s ease-out;
}

.about-section:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.12);
}

.about-section h2 {
    color: #1a4d1e;
    font-family: 'Playfair Display', serif;
    margin-bottom: 20px;
    border-bottom: 2px solid #e0e0e0;
    padding-bottom: 10px;
}

.about-section p {
    color: #333;
    line-height: 1.8;
    margin-bottom: 15px;
}

.team-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 25px;
    margin-top: 30px;
}

.team-card {
    background: white;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 6px 12px rgba(0,0,0,0.1);
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    animation: fadeIn 0.8s ease-out;
}

.team-card:hover {
    transform: translateY(-10px);
    box-shadow: 0 12px 24px rgba(0,0,0,0.15);
}

.team-image {
    height: 250px;
    overflow: hidden;
}

.team-image img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.5s ease;
}

.team-card:hover .team-image img {
    transform: scale(1.05);
}

.team-content {
    padding: 20px;
    background: linear-gradient(to bottom, #f8f9fa, #ffffff);
}

.team-name {
    font-family: 'Playfair Display', serif;
    font-size: 1.5rem;
    color: #1a4d1e;
    margin-bottom: 5px;
}

.team-role {
    color: #667eea;
    font-weight: 600;
    margin-bottom: 15px;
    font-size: 1rem;
}

.team-bio {
    color: #555;
    line-height: 1.6;
    margin-bottom: 15px;
}

.benefit-card {
    background: white;
    border-radius: 12px;
    padding: 25px;
    margin-bottom: 20px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.08);
    border-top: 4px solid #667eea;
    transition: all 0.3s ease;
}

.benefit-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 16px rgba(0,0,0,0.12);
}

.benefit-icon {
    font-size: 2.5rem;
    color: #764ba2;
    margin-bottom: 15px;
}

.benefit-title {
    font-weight: 700;
    color: #1a4d1e;
    margin-bottom: 10px;
    font-size: 1.2rem;
}

.benefit-desc {
    color: #555;
    line-height: 1.6;
}

/* Chat containers and other styles remain the same */
.chat-container {
    border-radius: 16px;
    padding: 20px;
    margin: 12px 5%;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    font-size: 15px;
    line-height: 1.6;
    animation: fadeIn 0.3s ease-in;
}

.user-container {
    background-color: #e8f5e9;
    color: #1a3c2e;
    margin-left: 30%;
    border-radius: 16px 16px 0 16px;
    border: 1px solid #c8e6c9;
}

.assistant-container {
    background-color: white;
    color: #1a3c2e;
    margin-right: 30%;
    border-radius: 16px 16px 16px 0;
    border: 1px solid #e0e0e0;
    border-left: 5px solid #4a9f4e;
}

.thinking-container {
    background-color: white;
    color: #1a3c2e;
    border-radius: 16px;
    padding: 20px;
    margin: 12px 5%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 30%;
    border: 1px dashed #a5d6a7;
}

.follow-up-section {
    margin: 20px 5% 10px 5%;
}

.follow-up-title {
    font-size: 15px;
    font-weight: 600;
    color: #1a4d1e;
    margin-bottom: 10px;
    padding-left: 5px;
}

.follow-up-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 12px;
}

.follow-up-btn {
    background-color: #e8f5e9;
    color: #1a4d1e;
    border: 1px solid #a5d6a7;
    border-radius: 12px;
    padding: 12px 15px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s ease;
    text-align: left;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.follow-up-btn:hover {
    background-color: #c8e6c9;
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    color: #1a3c2e;
}

.confidence-indicator {
    display: flex;
    align-items: center;
    margin-top: 12px;
    font-size: 14px;
    font-weight: 600;
    color: #1a3c2e;
}

.confidence-bar {
    width: 100px;
    height: 8px;
    border-radius: 4px;
    background: #e0e0e0;
    margin-right: 10px;
    overflow: hidden;
}

.confidence-fill {
    height: 100%;
    border-radius: 4px;
    background: #4a9f4e;
}

.stTextInput > div > div > input {
    border-radius: 16px;
    border: 2px solid #4a9f4e;
    padding: 14px;
    font-size: 15px;
    background-color: white;
}

.footer {
    text-align: center;
    color: #1a3c2e;
    font-size: 14px;
    margin-top: 40px;
    padding: 20px;
    background-color: white;
    border-radius: 16px;
    border: 1px solid #e0e0e0;
}

/* Navigation Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
}

.stTabs [data-baseweb="tab"] {
    height: 50px;
    padding: 0 25px;
    background: #e8f5e9 !important;
    border-radius: 12px !important;
    font-weight: 600;
    color: #1a4d1e !important;
    transition: all 0.3s ease !important;
    border: 1px solid #c8e6c9 !important;
}

.stTabs [data-baseweb="tab"]:hover {
    background: #c8e6c9 !important;
    color: #1a3c2e !important;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 4px 8px rgba(0,0,0,0.1) !important;
}

/* Animations */
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes slideUp {
    from { 
        opacity: 0;
        transform: translateY(20px);
    }
    to { 
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes scaleIn {
    from { 
        opacity: 0;
        transform: scale(0.9);
    }
    to { 
        opacity: 1;
        transform: scale(1);
    }
}

@media (max-width: 768px) {
    .user-container, .assistant-container {
        margin-left: 5% !important;
        margin-right: 5% !important;
    }

    .animated-title {
        font-size: 2rem !important;
    }
    
    .team-grid {
        grid-template-columns: 1fr;
    }
}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="sticky-header">
    <h1 class="animated-title">🌿 PQNK Farming Assistant</h1>
</div>
""", unsafe_allow_html=True)

# Navigation Tabs
tab1, tab2 = st.tabs(["Chat Assistant", "About PQNK"])

with tab1:
    # Sidebar
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-container">
            <div class="sidebar-logo">
                <img src="https://cdn-icons-png.flaticon.com/512/3079/3079158.png" alt="PQNK Logo">
            </div>
            <h2 class="sidebar-title">PQNK Farming</h2>
            <p class="sidebar-subtitle">Expert guidance for sustainable farming</p>
            <div style="text-align: center;">
                <button class="stButton" onclick="window.location.reload()">Clear Conversation</button>
            </div>
            <div class="sidebar-tips">
                <div class="sidebar-tips-title">Quick Tips:</div>
                <ul class="sidebar-tips-list">
                    <li>Ask about PQNK</li>
                    <li>Inquire about crop benefits</li>
                    <li>Explore implementation</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Initialize chat history
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'follow_ups' not in st.session_state:
        st.session_state.follow_ups = []

    # Display chat messages
    for message in st.session_state.messages:
        with st.container():
            if message["role"] == "user":
                st.markdown(
                    f"<div class='chat-container user-container'>{message['content']}</div>",
                    unsafe_allow_html=True
                )
            else:
                confidence_bar = ""
                if "confidence" in message:
                    confidence_bar = f"""
                    <div class='confidence-indicator'>
                        <div class='confidence-bar'>
                            <div class='confidence-fill' style='width: {message["confidence"]}%;'></div>
                        </div>
                        Confidence: {message["confidence"]}%
                    </div>
                    """
                st.markdown(
                    f"<div class='chat-container assistant-container'>{message['content']}{confidence_bar}</div>",
                    unsafe_allow_html=True
                )

    # Handle user input
    if prompt := st.chat_input("Ask about PQNK sustainable farming..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.follow_ups = []

        with st.spinner("Analyzing your question about PQNK farming..."):
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/ask",
                    json={"question": prompt},
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": data.get("answer", "No answer provided"),
                        "confidence": data.get("confidence", 0)
                    })
                    st.session_state.follow_ups = data.get("follow_ups", [])
                else:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"Error: API returned status {response.status_code}"
                    })
            except Exception as e:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Error: {str(e)}"
                })

        st.rerun()

    # Display follow-up questions if available
    if st.session_state.follow_ups and len(st.session_state.follow_ups) > 0:
        st.markdown("""
        <div class="follow-up-section">
            <div class="follow-up-title">Suggested Follow-up Questions:</div>
            <div class="follow-up-grid">
        """, unsafe_allow_html=True)

        for i, question in enumerate(st.session_state.follow_ups):
            if st.button(question, key=f"follow_up_{i}"):
                st.session_state.messages.append({"role": "user", "content": question})
                st.session_state.follow_ups = []

                with st.spinner("Analyzing your follow-up question..."):
                    try:
                        response = requests.post(
                            "http://127.0.0.1:8000/ask",
                            json={"question": question},
                            headers={"Content-Type": "application/json"},
                            timeout=30
                        )

                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": data.get("answer", "No answer provided"),
                                "confidence": data.get("confidence", 0)
                            })
                            st.session_state.follow_ups = data.get("follow_ups", [])
                    except Exception as e:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": f"Error processing follow-up: {str(e)}"
                        })

                st.rerun()

        st.markdown("</div></div>", unsafe_allow_html=True)

    # Footer
    st.markdown("""
    <div class="footer">
        <strong>PQNK Sustainable Farming Assistant</strong><br>
        Powered by xAI | Built with Streamlit | © 2025 PQNK Farming<br>
        Committed to regenerative agricultural practices
    </div>
    """, unsafe_allow_html=True)

with tab2:
    # About Page Content
    st.markdown("""
    <div class="about-header">
        <h1>About PQNK Farming</h1>
        <p>Revolutionizing agriculture through sustainable practices and AI-powered intelligence</p>
    </div>
    """, unsafe_allow_html=True)
    
    # What is PQNK Section
    st.markdown("""
    <div class="about-section">
        <h2>What is PQNK Farming?</h2>
        <p>PQNK Farming represents a paradigm shift in sustainable agriculture, combining cutting-edge biological solutions with advanced technology to create farming systems that are both highly productive and environmentally regenerative.</p>
        <p>At its core, PQNK focuses on enhancing soil microbiome health to create self-sustaining ecosystems that require fewer external inputs while delivering superior crop yields and nutritional quality. Our approach goes beyond organic farming to create truly regenerative systems that improve with each growing season.</p>
        <p>The PQNK methodology is built on three pillars:</p>
        <ul>
            <li><strong>Biological Optimization:</strong> Harnessing natural microbial communities to enhance plant health and soil fertility</li>
            <li><strong>Precision Monitoring:</strong> Advanced sensing and data collection for real-time ecosystem insights</li>
            <li><strong>Adaptive Management:</strong> AI-driven decision support that evolves with your farm's unique conditions</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # AI Benefits Section
    st.markdown("""
    <div class="about-section">
        <h2>The Power of AI in PQNK Farming</h2>
        <p>Our AI-powered assistant represents the next generation of agricultural decision support, combining vast datasets with deep learning to provide personalized recommendations for your farm.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Benefits Cards in Columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="benefit-card">
            <div class="benefit-icon">🌱</div>
            <h3 class="benefit-title">Microbiome Analysis</h3>
            <p class="benefit-desc">Our AI processes soil test results to recommend optimal microbial inoculants tailored to your specific conditions and crops.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="benefit-card">
            <div class="benefit-icon">📊</div>
            <h3 class="benefit-title">Predictive Analytics</h3>
            <p class="benefit-desc">Machine learning models forecast pest pressures, nutrient needs, and yield potential with remarkable accuracy.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="benefit-card">
            <div class="benefit-icon">🔄</div>
            <h3 class="benefit-title">Adaptive Learning</h3>
            <p class="benefit-desc">The system continuously improves its recommendations based on outcomes from thousands of similar farms.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="benefit-card">
            <div class="benefit-icon">🌍</div>
            <h3 class="benefit-title">Sustainability Metrics</h3>
            <p class="benefit-desc">Track and optimize your farm's carbon footprint, water usage, and biodiversity impact in real-time.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Team Section
    st.markdown("""
    <div class="about-section">
        <h2>Meet Our Team</h2>
        <p>The brilliant minds behind PQNK's revolutionary approach to sustainable agriculture.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Team Cards in Columns
    team_col1, team_col2 = st.columns(2)
    
    with team_col1:
        st.markdown("""
        <div class="team-card">
            <div class="team-image">
                <img src="https://images.unsplash.com/photo-1560250097-0b93528c311a?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=687&q=80" alt="Dr. Sarah Chen">
            </div>
            <div class="team-content">
                <h3 class="team-name">Dr. Sarah Chen</h3>
                <p class="team-role">Chief Scientist & Microbiome Expert</p>
                <p class="team-bio">PhD in Soil Microbiology from Stanford. 15 years experience in microbial ecology and plant-microbe interactions. Developed PQNK's core microbial formulations.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="team-card">
            <div class="team-image">
                <img src="https://images.unsplash.com/photo-1551836022-d5d88e9218df?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=687&q=80" alt="Elena Rodriguez">
            </div>
            <div class="team-content">
                <h3 class="team-name">Elena Rodriguez</h3>
                <p class="team-role">Director of Field Operations</p>
                <p class="team-bio">3rd generation farmer with agronomy degree from UC Davis. Leads our global network of demonstration farms and field trials.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with team_col2:
        st.markdown("""
        <div class="team-card">
            <div class="team-image">
                <img src="https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=687&q=80" alt="Raj Patel">
            </div>
            <div class="team-content">
                <h3 class="team-name">Raj Patel</h3>
                <p class="team-role">AI & Data Science Lead</p>
                <p class="team-bio">Former Google AI researcher specializing in agricultural applications. Built PQNK's predictive models and recommendation engines.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="team-card">
            <div class="team-image">
                <img src="https://images.unsplash.com/photo-1568602471122-7832951cc4c5?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1470&q=80" alt="Michael Johnson">
            </div>
            <div class="team-content">
                <h3 class="team-name">Michael Johnson</h3>
                <p class="team-role">Sustainability Economist</p>
                <p class="team-bio">Develops financial models proving the long-term profitability of regenerative practices. Former World Bank agriculture specialist.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Footer for About Page
    st.markdown("""
    <div class="footer">
        <strong>PQNK Sustainable Farming Initiative</strong><br>
        Transforming Agriculture Through Science & Technology<br>
        © 2025 PQNK Farming | Contact: info@pqnk.ag
    </div>
    """, unsafe_allow_html=True)