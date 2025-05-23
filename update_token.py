import requests
import os

# 🔐 Вставь сюда свой IAM API-ключ
IAM_API_KEY = "y0__xCr5436ARjB3RMghuL1mBNeikbzwoArv1Fp1P6EwNU8K03pqA"

# 📤 Запрос токена у Yandex IAM API
def get_iam_token(api_key):
    url = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
    headers = {"Content-Type": "application/json"}
    data = {
        "yandexPassportOauthToken": api_key  # ← это корректно только если у тебя OAuth-токен
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        token = response.json()["iamToken"]
        print("✅ Токен получен.")
        return token
    else:
        print("❌ Ошибка при получении токена:", response.status_code, response.text)
        return None

# 📝 Обновление secrets.toml
def write_to_secrets(iam_token):
    os.makedirs(".streamlit", exist_ok=True)
    path = os.path.join(".streamlit", "secrets.toml")

    with open(path, "w", encoding="utf-8") as f:
        f.write("[general]\n")
        f.write(f'YANDEX_API_KEY = "{iam_token}"\n')

    print(f"📦 secrets.toml обновлён: {path}")

# 🚀 Запуск
if __name__ == "__main__":
    token = get_iam_token(IAM_API_KEY)
    if token:
        write_to_secrets(token)
