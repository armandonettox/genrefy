![Genrefy](assets/logo.png)

Aplicacao que le as musicas curtidas do Spotify e as distribui automaticamente em playlists com base no genero dos artistas.

Acesse em: https://genrefy.armandonetto.com

## O que faz

- Busca todas as suas musicas curtidas no Spotify
- Identifica os generos de cada artista
- Distribui as musicas nas playlists conforme as regras configuradas em `config/production.json`

## Funcionalidades

| Aba | Descricao |
|-----|-----------|
| Reload | Executa a distribuicao: esvazia e repopula todas as playlists configuradas |
| Check | Lista artistas sem mapeamento de genero (nao entram em nenhuma playlist) |
| Info | Mostra os generos de um artista pelo ID ou URL do Spotify |
| Genres | Exporta CSV com todos os artistas e seus generos |

## Configuracao das playlists

Edite `config/production.json` para definir quais generos vao para qual playlist:

| Campo | Descricao |
|-------|-----------|
| `id` | ID da playlist (do URL do Spotify) |
| `name` | Nome da playlist (so para identificacao no log) |
| `genres` | Generos que entram na playlist |
| `ngenres` | Generos que nunca entram na playlist, mesmo que o artista tenha outros generos que batem |
| `aoverride` | Artistas especificos forcados para a playlist, independente do genero |

## Stack

- Python 3.12
- Streamlit
- spotipy
- Podman + podman-compose
- nginx (reverse proxy)
- Oracle Cloud VM

## Deploy

O app roda em um container Podman na Oracle Cloud. O deploy e feito automaticamente via GitHub Actions ao fazer push na branch `master`.
