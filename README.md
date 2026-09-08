 
# Compilação
(Windows)

Para compilar o projeto, execute o comando abaixo para gerar o motor em C. (necessita da pasta mingw64)
```
mingw64\bin\gcc.exe -shared -m64 -O3 -o src\motor_lsystem.dll src\motor_lsystem.c -lm  
```
Instale as dependências do python
```
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

Rode o arquivo main.py
```
cd src
python ./main.py
```