# 🚀 AI Recruitment Agent

An AI-powered recruitment assistant that helps recruiters efficiently screen candidates by analyzing resumes against a job description, ranking applicants, identifying skill gaps, and generating personalized interview questions.

## 🌐 Live Demo

**Application:** https://recruitment-agent-dijaj7wpqkefgspkjs5daq.streamlit.app/

## 💻 GitHub Repository

https://github.com/JayanthReddy3010/Recruitment-Agent

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
git clone https://github.com/<your-username>/<repository-name>.git
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

(Add Screenshot)

### Resume Screening

(Add Screenshot)

### Candidate Ranking

(Add Screenshot)

### Interview Questions

(Add Screenshot)

### Generated Report

(Add Screenshot)

---

## 👨‍💻 Developed By

**Gunreddy Jayanth Reddy**

B.Tech Computer Science And Engineering

Vardhaman College of Engineering

---

## 📜 License

This project is developed for educational and hackathon purposes.
