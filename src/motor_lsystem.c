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
    float x, y, z;
    float hx, hy, hz; 
    float lx, ly, lz; 
    float ux, uy, uz; 
    int profundidade;
} EstadoPilha;

typedef struct {
    float prob_acumulada;
    char* substituicao;
    size_t len;
} RegraEstocastica;

typedef struct {
    int num_opcoes;
    RegraEstocastica opcoes[10];
} ConjuntoRegras;

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
    if(!seeded) { srand((unsigned int)time(NULL)); seeded = 1; }

    ConjuntoRegras regras[256];
    parse_regras(regras_in, regras);

    size_t len = strlen(axioma);
    char* atual = (char*)malloc(len + 1);
    if (!atual) { free_regras(regras); return NULL; }
    strcpy(atual, axioma);

    for (int n = 0; n < iteracoes; n++) {
        size_t cap = len * 2 + 128;
        char* proximo = (char*)malloc(cap);
        if (!proximo) { free(atual); free_regras(regras); return NULL; }
        size_t pos = 0;

        for (size_t i = 0; i < len; i++) {
            unsigned char c = atual[i];
            
            if (regras[c].num_opcoes > 0) {
                float total_prob = regras[c].opcoes[regras[c].num_opcoes - 1].prob_acumulada;
                float r = ((float)rand() / (float)RAND_MAX) * total_prob;
                
                RegraEstocastica* escolhida = &regras[c].opcoes[0];
                for(int j = 0; j < regras[c].num_opcoes; j++) {
                    if(r <= regras[c].opcoes[j].prob_acumulada) { escolhida = &regras[c].opcoes[j]; break; }
                }

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

void rotacionar(float angle, float ax, float ay, float az, float* vx, float* vy, float* vz) {
    float c = cosf(angle);
    float s = sinf(angle);
    float dot = (*vx)*ax + (*vy)*ay + (*vz)*az;
    float nx = (*vx)*c + s*(ay*(*vz) - az*(*vy)) + ax*dot*(1-c);
    float ny = (*vy)*c + s*(az*(*vx) - ax*(*vz)) + ay*dot*(1-c);
    float nz = (*vz)*c + s*(ax*(*vy) - ay*(*vx)) + az*dot*(1-c);
    *vx = nx; *vy = ny; *vz = nz;
}

EXPORT float* calcular_vertices_c(const char* instrucoes, float angulo_graus, float tamanho_linha, int* out_num_vertices) {
    float a = angulo_graus * (3.14159265358979323846f / 180.0f);
    float x = 0.0f, y = 0.0f, z = 0.0f;
    float hx = 0.0f, hy = 1.0f, hz = 0.0f; 
    float lx = -1.0f, ly = 0.0f, lz = 0.0f;
    float ux = 0.0f, uy = 0.0f, uz = 1.0f; 
    int profundidade = 0;

    int num_segmentos = 0;
    for (int i = 0; instrucoes[i] != '\0'; i++) {
        char c = instrucoes[i];
        if (c == 'F' || c == 'A' || c == 'B') num_segmentos++;
    }

    *out_num_vertices = num_segmentos * 2;
    if (num_segmentos == 0) return NULL;

    float* vertices = (float*)malloc(num_segmentos * 8 * sizeof(float));
    if (!vertices) return NULL;

    int p_cap = 1000, p_topo = 0;
    EstadoPilha* pilha = (EstadoPilha*)malloc(p_cap * sizeof(EstadoPilha));
    
    int v = 0;
    for (int i = 0; instrucoes[i] != '\0'; i++) {
        char c = instrucoes[i];
        if (c == 'F' || c == 'A' || c == 'B') {
            float nx = x + hx * tamanho_linha;
            float ny = y + hy * tamanho_linha;
            float nz = z + hz * tamanho_linha;
            vertices[v++] = x; vertices[v++] = y; vertices[v++] = z; vertices[v++] = (float)profundidade;
            vertices[v++] = nx; vertices[v++] = ny; vertices[v++] = nz; vertices[v++] = (float)profundidade;
            x = nx; y = ny; z = nz;
        } 
        else if (c == '+') { rotacionar(a, ux, uy, uz, &hx, &hy, &hz); rotacionar(a, ux, uy, uz, &lx, &ly, &lz); }
        else if (c == '-') { rotacionar(-a, ux, uy, uz, &hx, &hy, &hz); rotacionar(-a, ux, uy, uz, &lx, &ly, &lz); }
        else if (c == '&') { rotacionar(a, lx, ly, lz, &hx, &hy, &hz); rotacionar(a, lx, ly, lz, &ux, &uy, &uz); }
        else if (c == '^') { rotacionar(-a, lx, ly, lz, &hx, &hy, &hz); rotacionar(-a, lx, ly, lz, &ux, &uy, &uz); }
        else if (c == '\\' || c == '<') { rotacionar(a, hx, hy, hz, &lx, &ly, &lz); rotacionar(a, hx, hy, hz, &ux, &uy, &uz); }
        else if (c == '/' || c == '>') { rotacionar(-a, hx, hy, hz, &lx, &ly, &lz); rotacionar(-a, hx, hy, hz, &ux, &uy, &uz); }
        else if (c == '|') { rotacionar(3.14159f, ux, uy, uz, &hx, &hy, &hz); rotacionar(3.14159f, ux, uy, uz, &lx, &ly, &lz); }
        else if (c == '[') {
            if (p_topo >= p_cap) {
                p_cap *= 2;
                pilha = (EstadoPilha*)realloc(pilha, p_cap * sizeof(EstadoPilha));
            }
            pilha[p_topo++] = (EstadoPilha){x, y, z, hx, hy, hz, lx, ly, lz, ux, uy, uz, profundidade};
            profundidade++;
        } 
        else if (c == ']') {
            if (p_topo > 0) {
                p_topo--;
                x = pilha[p_topo].x; y = pilha[p_topo].y; z = pilha[p_topo].z;
                hx = pilha[p_topo].hx; hy = pilha[p_topo].hy; hz = pilha[p_topo].hz;
                lx = pilha[p_topo].lx; ly = pilha[p_topo].ly; lz = pilha[p_topo].lz;
                ux = pilha[p_topo].ux; uy = pilha[p_topo].uy; uz = pilha[p_topo].uz;
                profundidade = pilha[p_topo].profundidade;
            }
        }
    }
    free(pilha);
    return vertices;
}

EXPORT float* calcular_folhas_c(const char* instrucoes, float angulo_graus, float tamanho_linha, int* out_num_vertices) {
    float a = angulo_graus * (3.14159265358979323846f / 180.0f);
    float x = 0.0f, y = 0.0f, z = 0.0f;
    float hx = 0.0f, hy = 1.0f, hz = 0.0f; 
    float lx = -1.0f, ly = 0.0f, lz = 0.0f;
    float ux = 0.0f, uy = 0.0f, uz = 1.0f; 
    int profundidade = 0;

    int num_folhas = 0;
    for (int i = 0; instrucoes[i] != '\0'; i++) {
        if (instrucoes[i] == '@') num_folhas++;
    }

    // Agora cada folha possui 2 triângulos (6 vértices) para garantir formato dobrado 3D
    *out_num_vertices = num_folhas * 6; 
    if (num_folhas == 0) return NULL;

    float* vertices = (float*)malloc(num_folhas * 24 * sizeof(float)); 
    if (!vertices) return NULL;

    int p_cap = 1000, p_topo = 0;
    EstadoPilha* pilha = (EstadoPilha*)malloc(p_cap * sizeof(EstadoPilha));
    
    int v = 0;
    for (int i = 0; instrucoes[i] != '\0'; i++) {
        char c = instrucoes[i];
        if (c == 'F' || c == 'A' || c == 'B') {
            x += hx * tamanho_linha;
            y += hy * tamanho_linha;
            z += hz * tamanho_linha;
        } 
        else if (c == '@') {
            float scale = tamanho_linha * 1.5f;
            float fold = scale * 0.3f; // Deslocamento ao longo da Normal (Up) para criar o vinco
            
            float bx = x, by = y, bz = z; 
            float tx = x + hx * scale, ty = y + hy * scale, tz = z + hz * scale;
            
            float lx_pos = x + (hx + lx) * scale * 0.5f + ux * fold;
            float ly_pos = y + (hy + ly) * scale * 0.5f + uy * fold;
            float lz_pos = z + (hz + lz) * scale * 0.5f + uz * fold;

            float rx_pos = x + (hx - lx) * scale * 0.5f + ux * fold;
            float ry_pos = y + (hy - ly) * scale * 0.5f + uy * fold;
            float rz_pos = z + (hz - lz) * scale * 0.5f + uz * fold;

            // Triângulo 1 (Metade Esquerda)
            vertices[v++] = bx; vertices[v++] = by; vertices[v++] = bz; vertices[v++] = (float)profundidade;
            vertices[v++] = lx_pos; vertices[v++] = ly_pos; vertices[v++] = lz_pos; vertices[v++] = (float)profundidade;
            vertices[v++] = tx; vertices[v++] = ty; vertices[v++] = tz; vertices[v++] = (float)profundidade;

            // Triângulo 2 (Metade Direita)
            vertices[v++] = bx; vertices[v++] = by; vertices[v++] = bz; vertices[v++] = (float)profundidade;
            vertices[v++] = tx; vertices[v++] = ty; vertices[v++] = tz; vertices[v++] = (float)profundidade;
            vertices[v++] = rx_pos; vertices[v++] = ry_pos; vertices[v++] = rz_pos; vertices[v++] = (float)profundidade;
        }
        else if (c == '+') { rotacionar(a, ux, uy, uz, &hx, &hy, &hz); rotacionar(a, ux, uy, uz, &lx, &ly, &lz); }
        else if (c == '-') { rotacionar(-a, ux, uy, uz, &hx, &hy, &hz); rotacionar(-a, ux, uy, uz, &lx, &ly, &lz); }
        else if (c == '&') { rotacionar(a, lx, ly, lz, &hx, &hy, &hz); rotacionar(a, lx, ly, lz, &ux, &uy, &uz); }
        else if (c == '^') { rotacionar(-a, lx, ly, lz, &hx, &hy, &hz); rotacionar(-a, lx, ly, lz, &ux, &uy, &uz); }
        else if (c == '\\' || c == '<') { rotacionar(a, hx, hy, hz, &lx, &ly, &lz); rotacionar(a, hx, hy, hz, &ux, &uy, &uz); }
        else if (c == '/' || c == '>') { rotacionar(-a, hx, hy, hz, &lx, &ly, &lz); rotacionar(-a, hx, hy, hz, &ux, &uy, &uz); }
        else if (c == '|') { rotacionar(3.14159f, ux, uy, uz, &hx, &hy, &hz); rotacionar(3.14159f, ux, uy, uz, &lx, &ly, &lz); }
        else if (c == '[') {
            if (p_topo >= p_cap) {
                p_cap *= 2;
                pilha = (EstadoPilha*)realloc(pilha, p_cap * sizeof(EstadoPilha));
            }
            pilha[p_topo++] = (EstadoPilha){x, y, z, hx, hy, hz, lx, ly, lz, ux, uy, uz, profundidade};
            profundidade++;
        } 
        else if (c == ']') {
            if (p_topo > 0) {
                p_topo--;
                x = pilha[p_topo].x; y = pilha[p_topo].y; z = pilha[p_topo].z;
                hx = pilha[p_topo].hx; hy = pilha[p_topo].hy; hz = pilha[p_topo].hz;
                lx = pilha[p_topo].lx; ly = pilha[p_topo].ly; lz = pilha[p_topo].lz;
                ux = pilha[p_topo].ux; uy = pilha[p_topo].uy; uz = pilha[p_topo].uz;
                profundidade = pilha[p_topo].profundidade;
            }
        }
    }
    free(pilha);
    return vertices;
}

EXPORT void liberar_memoria_c(char* ponteiro) { if (ponteiro) free(ponteiro); }
EXPORT void liberar_vertices_c(float* ponteiro) { if (ponteiro) free(ponteiro); }