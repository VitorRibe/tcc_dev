#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

typedef struct {
    float x, y, direcao;
} EstadoPilha;

typedef struct {
    float prob_acumulada;
    char* substituicao;
    size_t len;
} RegraEstocastica;

typedef struct {
    int num_opcoes;
    RegraEstocastica opcoes[10]; // Limite fixo de 10 variações por regra para performance
} ConjuntoRegras;

// Faz o parsing das strings de regra em C (ex: "0.3:F[+F],0.7:F[-F]")
void parse_regras(const char** regras_in, ConjuntoRegras* regras_out) {
    for(int i = 0; i < 256; i++) {
        regras_out[i].num_opcoes = 0;
        if(regras_in[i] == NULL) continue;

        char* str = strdup(regras_in[i]);
        char* token = strtok(str, ",");
        float soma_prob = 0.0f;

        while(token != NULL && regras_out[i].num_opcoes < 10) {
            char* dois_pontos = strchr(token, ':');
            float prob = 1.0f;
            char* sub = token;

            if(dois_pontos != NULL) {
                *dois_pontos = '\0';
                prob = atof(token);
                sub = dois_pontos + 1;
            }

            soma_prob += prob;

            RegraEstocastica* r = &regras_out[i].opcoes[regras_out[i].num_opcoes];
            r->prob_acumulada = soma_prob;
            r->substituicao = strdup(sub);
            r->len = strlen(sub);
            regras_out[i].num_opcoes++;

            token = strtok(NULL, ",");
        }
        free(str);
    }
}

void free_regras(ConjuntoRegras* regras) {
    for(int i = 0; i < 256; i++) {
        for(int j = 0; j < regras[i].num_opcoes; j++) {
            free(regras[i].opcoes[j].substituicao);
        }
    }
}

EXPORT char* expandir_lsystem_c(const char* axioma, const char** regras_in, int iteracoes) {
    static int seeded = 0;
    if(!seeded) { 
        srand((unsigned int)time(NULL)); 
        seeded = 1; 
    }

    ConjuntoRegras regras[256];
    parse_regras(regras_in, regras);

    size_t len = strlen(axioma);
    char* atual = (char*)malloc(len + 1);
    if (!atual) {
        free_regras(regras);
        return NULL;
    }
    strcpy(atual, axioma);

    for (int n = 0; n < iteracoes; n++) {
        size_t cap = len * 2 + 128; // Buffer dinâmico pré-alocado
        char* proximo = (char*)malloc(cap);
        if (!proximo) {
            free(atual);
            free_regras(regras);
            return NULL;
        }
        size_t pos = 0;

        for (size_t i = 0; i < len; i++) {
            unsigned char c = atual[i];
            
            if (regras[c].num_opcoes > 0) {
                // Seleção roleta estocástica baseada nos pesos
                float total_prob = regras[c].opcoes[regras[c].num_opcoes - 1].prob_acumulada;
                float r = ((float)rand() / (float)RAND_MAX) * total_prob;
                
                RegraEstocastica* escolhida = &regras[c].opcoes[0];
                for(int j = 0; j < regras[c].num_opcoes; j++) {
                    if(r <= regras[c].opcoes[j].prob_acumulada) {
                        escolhida = &regras[c].opcoes[j];
                        break;
                    }
                }

                // Realocação geométrica da memória se o buffer encher
                if (pos + escolhida->len >= cap) {
                    cap = (cap + escolhida->len) * 2;
                    char* temp = (char*)realloc(proximo, cap);
                    if (!temp) { free(proximo); free(atual); free_regras(regras); return NULL; }
                    proximo = temp;
                }
                memcpy(proximo + pos, escolhida->substituicao, escolhida->len);
                pos += escolhida->len;
            } else {
                if (pos + 1 >= cap) {
                    cap = cap * 2;
                    char* temp = (char*)realloc(proximo, cap);
                    if (!temp) { free(proximo); free(atual); free_regras(regras); return NULL; }
                    proximo = temp;
                }
                proximo[pos++] = c;
            }
        }
        proximo[pos] = '\0';
        free(atual);
        atual = proximo;
        len = pos;
    }

    free_regras(regras);
    return atual;
}

EXPORT float* calcular_vertices_c(const char* instrucoes, float angulo_graus, float tamanho_linha, int* out_num_vertices) {
    float angulo_rad = angulo_graus * (3.14159265358979323846f / 180.0f);
    float x = 0.0f, y = 0.0f;
    float direcao = 3.14159265358979323846f / 2.0f;

    int num_segmentos = 0;
    for (int i = 0; instrucoes[i] != '\0'; i++) {
        char c = instrucoes[i];
        if (c == 'F' || c == 'A' || c == 'B' || c == 'X' || c == 'Y') {
            if (c == 'F' || c == 'A' || c == 'B') num_segmentos++;
        }
    }

    *out_num_vertices = num_segmentos * 2;
    if (num_segmentos == 0) return NULL;

    float* vertices = (float*)malloc(num_segmentos * 4 * sizeof(float));
    if (!vertices) return NULL;

    int pilha_capacidade = 1000;
    int pilha_topo = 0;
    EstadoPilha* pilha = (EstadoPilha*)malloc(pilha_capacidade * sizeof(EstadoPilha));
    if (!pilha) { free(vertices); return NULL; }

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
            x = nx; y = ny;
        } else if (c == '+') {
            direcao -= angulo_rad;
        } else if (c == '-') {
            direcao += angulo_rad;
        } else if (c == '[') {
            if (pilha_topo >= pilha_capacidade) {
                pilha_capacidade *= 2;
                EstadoPilha* temp = (EstadoPilha*)realloc(pilha, pilha_capacidade * sizeof(EstadoPilha));
                if (!temp) { free(pilha); free(vertices); return NULL; }
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

EXPORT void liberar_memoria_c(char* ponteiro) { if (ponteiro) free(ponteiro); }
EXPORT void liberar_vertices_c(float* ponteiro) { if (ponteiro) free(ponteiro); }