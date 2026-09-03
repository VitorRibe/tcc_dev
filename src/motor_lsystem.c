#include <stdlib.h>
#include <string.h>
#include <math.h>

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

typedef struct {
    float x, y, direcao;
} EstadoPilha;

EXPORT char* expandir_lsystem_c(const char* axioma, const char** regras, int iteracoes) {
    size_t len = strlen(axioma);
    char* atual = (char*)malloc(len + 1);
    if (!atual) return NULL;
    strcpy(atual, axioma);

    size_t regras_len[256] = {0};
    for (int i = 0; i < 256; i++) {
        if (regras[i] != NULL) {
            regras_len[i] = strlen(regras[i]);
        }
    }

    for (int n = 0; n < iteracoes; n++) {
        size_t novo_tamanho = 0;
        for (size_t i = 0; i < len; i++) {
            unsigned char c = atual[i];
            novo_tamanho += (regras[c] != NULL) ? regras_len[c] : 1;
        }

        char* proximo = (char*)malloc(novo_tamanho + 1);
        if (!proximo) {
            free(atual);
            return NULL; 
        }

        size_t pos = 0;
        for (size_t i = 0; i < len; i++) {
            unsigned char c = atual[i];
            if (regras[c] != NULL) {
                memcpy(proximo + pos, regras[c], regras_len[c]);
                pos += regras_len[c];
            } else {
                proximo[pos++] = c;
            }
        }
        proximo[novo_tamanho] = '\0';

        free(atual);
        atual = proximo;
        len = novo_tamanho;
    }

    return atual;
}

EXPORT void liberar_memoria_c(char* ponteiro) {
    if (ponteiro != NULL) {
        free(ponteiro);
    }
}

EXPORT float* calcular_vertices_c(const char* instrucoes, float angulo_graus, float tamanho_linha, int* out_num_vertices) {
    float angulo_rad = angulo_graus * (3.14159265358979323846f / 180.0f);
    float x = 0.0f, y = 0.0f;
    float direcao = 3.14159265358979323846f / 2.0f;

    int num_segmentos = 0;
    for (int i = 0; instrucoes[i] != '\0'; i++) {
        char c = instrucoes[i];
        if (c == 'F' || c == 'A' || c == 'B') {
            num_segmentos++;
        }
    }

    *out_num_vertices = num_segmentos * 2;
    if (num_segmentos == 0) return NULL;

    float* vertices = (float*)malloc(num_segmentos * 4 * sizeof(float));
    if (!vertices) return NULL;

    int pilha_capacidade = 1000;
    int pilha_topo = 0;
    EstadoPilha* pilha = (EstadoPilha*)malloc(pilha_capacidade * sizeof(EstadoPilha));
    if (!pilha) {
        free(vertices);
        return NULL;
    }

    int v_idx = 0;
    for (int i = 0; instrucoes[i] != '\0'; i++) {
        char c = instrucoes[i];
        if (c == 'F' || c == 'A' || c == 'B') {
            float nx = x + cosf(direcao) * tamanho_linha;
            float ny = y + sinf(direcao) * tamanho_linha;
            
            vertices[v_idx++] = x;
            vertices[v_idx++] = y;
            vertices[v_idx++] = nx;
            vertices[v_idx++] = ny;
            
            x = nx;
            y = ny;
        } else if (c == '+') {
            direcao -= angulo_rad;
        } else if (c == '-') {
            direcao += angulo_rad;
        } else if (c == '[') {
            if (pilha_topo >= pilha_capacidade) {
                pilha_capacidade *= 2;
                EstadoPilha* temp = (EstadoPilha*)realloc(pilha, pilha_capacidade * sizeof(EstadoPilha));
                if (!temp) {
                    free(pilha);
                    free(vertices);
                    return NULL;
                }
                pilha = temp;
            }
            pilha[pilha_topo++] = (EstadoPilha){x, y, direcao};
        } else if (c == ']') {
            if (pilha_topo > 0) {
                pilha_topo--;
                x = pilha[pilha_topo].x;
                y = pilha[pilha_topo].y;
                direcao = pilha[pilha_topo].direcao;
            }
        }
    }

    free(pilha);
    return vertices;
}

EXPORT void liberar_vertices_c(float* ponteiro) {
    if (ponteiro != NULL) {
        free(ponteiro);
    }
}