![Genrefy](assets/logo.png)

Acesse em: https://genrefy.armandonetto.com

---

O Genrefy lê as músicas curtidas do Spotify e as distribui automaticamente em playlists com base no gênero dos artistas.

A ideia surgiu da frustração de ter centenas de músicas curtidas misturadas sem organização. Em vez de criar playlists manualmente, o Genrefy faz isso automaticamente: você configura quais gêneros pertencem a cada playlist, conecta sua conta do Spotify e manda sincronizar. Ele varre todas as suas músicas curtidas, identifica os gêneros de cada artista via API do Spotify e distribui as faixas nas playlists certas.

## O que faz

<img width="1019" height="468" alt="landing-page" src="https://github.com/user-attachments/assets/5441df9a-e152-45cd-a3a7-e24e453fa339" />

- Autentica com a conta do Spotify via OAuth
- Busca todas as músicas curtidas do usuário
- Identifica os gêneros de cada artista pela API do Spotify
- Distribui as músicas nas playlists conforme as regras configuradas
- Permite configurar playlists, gêneros incluídos, gêneros excluídos e artistas fixos direto pelo app
- Mostra quais artistas não têm gênero mapeado em nenhuma playlist
- Exporta CSV com todos os artistas e seus gêneros.
