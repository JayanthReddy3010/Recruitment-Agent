# 🚀 AI Recruitment Agent

An AI-powered recruitment assistant that helps recruiters efficiently screen candidates by analyzing resumes against a job description, ranking applicants, identifying skill gaps, and generating personalized interview questions.

## 🌐 Live Demo

**Application:** https://recruitment-agent-dijaj7wpqkefgspkjs5daq.streamlit.app/

## 💻 GitHub Repository

https://github.com/JayanthReddy3010/Recruitment-Agent

## 📽️ Demo Video

https://youtu.be/your-video-id

## 📑 Project Presentation (PPT)

https://drive.google.com/file/d/your-file-id/view

---

## 📌 Project Overview

The AI Recruitment Agent simplifies the hiring process by automating resume screening using Generative AI and Retrieval-Augmented Generation (RAG). The application compares candidate resumes with a job description and provides intelligent hiring insights.

---

## ✨ Features

- 📄 Upload multiple candidate resumes (PDF)
- 📋 Upload or use the sample Job Description
- 📊 AI-powered resume screening
- 🎯 Candidate ranking based on JD match
- 🧠 Skill gap analysis
- 💬 AI-generated interview questions
- ⚠️ Candidate strengths and red flags
- 📑 Downloadable recruitment report (PDF)
- 🔍 Semantic search using ChromaDB
- 🤖 Google Gemini-powered reasoning
- 🧪 Built-in demo resumes and sample JD

---

## 🛠 Tech Stack

### Frontend
- Streamlit

### Backend
- Python

### AI Models
- Google Gemini API
- (Gemma 4 if used)

### Vector Database
- ChromaDB

### Document Processing
- PyPDF
- PDFPlumber

### Libraries
- LangChain
- Pandas
- FPDF2
- Tavily Search API
- Pydantic

---

## 📂 Project Structure

```
Recruitment-Agent/
│
├── app.py
├── agent.py
├── config.py
├── requirements.txt
├── README.md
│
├── data/
│   ├── resumes_pdf/
│   ├── resumes/
│   └── job_description.txt
│
├── reports/
│
└── .streamlit/
```

---

## 🚀 Installation

Clone the repository

```bash
git clone https://github.com/JayanthReddy3010/Recruitment-Agent.git
```

Go into the project

```bash
cd Recruitment-Agent
```

Install dependencies

```bash
pip install -r requirements.txt
```

Create a `.env`

```env
GEMINI_API_KEY=YOUR_API_KEY
TAVILY_API_KEY=YOUR_API_KEY
```

Run

```bash
streamlit run app.py
```

---

## 📸 Screenshots

### Home Page

<img width="2870" height="1380" alt="image" src="https://github.com/user-attachments/assets/49ae7093-b102-487f-9019-11b4919c675e" />


### Candidate Ranking

<img width="2874" height="1322" alt="image" src="https://github.com/user-attachments/assets/d0e70f3c-a954-4d0f-905b-28e5237313d4" />


### Interview Questions

<img width="1926" height="1154" alt="image" src="https://github.com/user-attachments/assets/0602ca3c-99ae-4bd3-b474-9e5619fc5494" />


---

## 👨‍💻 Developed By

**Gunreddy Jayanth Reddy**

B.Tech Computer Science And Engineering

Vardhaman College of Engineering

---

## 📜 License

This project is developed for educational and hackathon purposes.
