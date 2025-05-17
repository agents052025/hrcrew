# AI-система для автоматичного аналізу та порівняння резюме з вимогами вакансії

Це багатокомпонентна система на основі CrewAI для обробки резюме, аналізу навичок, дослідження кандидатів та формування детальних звітів про відповідність вакансіям.

## Можливості

- 📄 **Парсинг резюме**: Підтримка PDF, DOCX, HTML, TXT
- 🤖 **Мультиагентний аналіз**: Спеціалізовані агенти для обробки документів, аналізу навичок, дослідження кандидатів тощо
- 🔄 **Гнучкість LLM**: Працює з OpenAI та локальними моделями Ollama
- 📊 **Детальні звіти**: Оцінка навичок, досвіду, рекомендації щодо найму
- 🌐 **Веб-інтерфейс**: Зручний Streamlit UI для завантаження резюме та аналізу
- ⚙️ **Гнучке налаштування**: Зміна моделей та параметрів через UI або config.yaml

## Архітектура

- **Парсер документів**: Витягує структуровану інформацію з резюме
- **Агентна система**: 7 спеціалізованих агентів для аналізу та генерації звіту
- **Конфігурація**: Гнучке налаштування моделей та агентів через config.yaml
- **Веб-інтерфейс**: Streamlit для взаємодії з користувачем

### Ролі агентів

- Обробка документів
- Аналіз навичок та досвіду
- Аналіз опису вакансії
- Дослідження кандидата (пошук у відкритих джерелах)
- Розрахунок відповідності (Match Score)
- Генерація фінального звіту
- Обробка зворотного зв'язку

## Встановлення

### Необхідне

- Python 3.9+
- [Ollama](https://ollama.ai/) (опційно, для локальних LLM)

### Кроки

1. Клонувати репозиторій:
   ```bash
   git clone https://github.com/yourusername/resume-screening-system.git
   cd resume-screening-system
   ```

2. Створити та активувати віртуальне середовище:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. Встановити залежності:
   ```bash
   pip install -r requirements.txt
   ```

4. Створити файл `.env` з ключами:
   ```
   OPENAI_API_KEY=ваш-openai-api-ключ
   BRAVE_API_KEY=ваш-brave-search-api-ключ
   ```

## Налаштування

Всі параметри можна змінювати у файлі `config.yaml` або через веб-інтерфейс:

```yaml
llm:
  provider: "openai"  # або "ollama"

  openai:
    model_name: "gpt-3.5-turbo"
    temperature: 0.7
    max_tokens: 2000

  ollama:
    server_url: "http://localhost:11434"
    model_name: "mistral"
    temperature: 0.7
    max_tokens: 2000

  agent_specific:
    document_processor:
      provider: "ollama"
      model_name: "mistral"
      temperature: 0.3
    researcher:
      provider: "ollama"
      model_name: "mistral"
      temperature: 0.5
    matcher:
      provider: "openai"
      model_name: "gpt-3.5-turbo"
      temperature: 0.3
      max_tokens: 1000
    report_generator:
      provider: "openai"
      model_name: "gpt-3.5-turbo"
      temperature: 0.3
      max_tokens: 1000
```

## Використання

### Веб-інтерфейс

1. Запустіть Streamlit:
   ```bash
   python -m streamlit run app.py
   ```
2. Відкрийте браузер: http://localhost:8501
3. Налаштуйте LLM у сайдбарі
4. Завантажте резюме та введіть опис вакансії
5. Натисніть "Аналізувати"

### Командний рядок

```bash
./run.sh --openai
./run.sh --ollama
./run.sh --parse-only
./run.sh --output results.json
./run.sh --compare "Software Engineer"
./run.sh --list-reports
```

## Робота з Ollama

1. Встановіть Ollama: https://ollama.ai/download
2. Завантажте модель:
   ```bash
   ollama pull mistral
   ```
3. Запустіть сервер:
   ```bash
   ollama serve
   ```
4. Вкажіть Ollama у config.yaml або через веб-інтерфейс

## Тестування

```bash
pytest tests/
```

## Структура директорій

- `resumes/` — зразки резюме
- `job_descriptions/` — описи вакансій
- `reports/` — збережені звіти
- `tests/` — тести

## Типові проблеми

- **0/100 у Match Score:** Перевірте, чи модель повертає числовий бал, чи правильно налаштовано agent_specific.
- **Помилка з BRAVE_API_KEY:** Додайте ключ у .env.

## Ліцензія

MIT 
MIT 
This project is licensed under the MIT License - see the LICENSE file for details. 
