# Base Nimbus
+ Main generico que busca outras classes de comandos no projeto, ai não precisa ficar mexendo no main quando for adicionar coisa nova
    + melhor seria usar um decorator estilo `add_to_main` ou algo assim, que só pega adiciona tal classe numa global somewhere,
      tipo o DataCache. De preferencia tal classe nao pode receber params no construtor.
    + toma cuidado com onde estao tais scripts: tal decorator/global não podem estar no nimbus/main, senão pode dar cyclic-import


# Media Organizer (files/series)
- portar organizer pra cá
    - poder setar pasta de media e etc via config (salva no Cache)
    - talvez poder definir settings padrão?
    - talvez ler settings de alguma pasta?
    - talvez separar alguns comandos, alem do "organize downloads" padrão
        - poder reorganizar as coisas de midia dentro dela mesma seria util
    - talvez renomear um pouco? tamo falando "media" mas é mostly filmes/series, nada de musica.
        - altho, talvez possamos suportar musicas tb? Em vez de Serie/Season/epi seria algo tipo Artista/Album/musica

- adicionar suporte a pegar dados de um filme/serie do IMDB (principalmente o seu "IMDB code")
- adicionar suporte a verificar torrents de filmes pela API do YTS
    - https://yts.mx/api#movie_details
    - e poder baixar eles tb
- adicionar suport a verificar torrents de series pela API do EZTV
    - https://eztv.re/api/get-torrents
        - params:
            - `limit`: results per page, between 1-100
            - `page`: current page of results
            - `imdb_id`: filter results to only those of this show/movie
        - exemplo: `https://eztv.re/api/get-torrents?imdb_id=6048596&limit=10&page=1`
    - e poder baixar eles tb

- poder já ligar o torrent-client pra baixar tais torrents
    - tem que fechar o torrent-client depois de baixar as coisas
    - qual torrent-client usar? seria bom se desse pra configurar em vez de ser fixo em um
        - pelo menos o Transmission seria util aceitar pq é o que usamos atualmente

- [FLUXO]:
    - verifica se tem torrent (pelas APIs) do que queremos
    - se tiver pelo menos 1:
        - baixa torrents dos sites (pelas APIs)
        - liga torrent-cliente pra baixar os coisas de media usando os torrents
        - fecha torrent-cliente
        - organiza arquivos de media
        - atualiza Plex? <ver como>


# Musicas
- portar outros scripts meus pra cá:
    - Documents/Carro/Musicas:
        - CarroMusicExporter.py
        - fixPlaylists.py
- ver se poderia "juntar" com o resto de media/organizer (files e series)


# Backup do Sistema
- Criar/Definir um Backup:
    - definir sources: arquivos/pastas a copiar
        - no caso de pastas, poder escolher ser recursivo ou não e poder definir uma blacklist pra ignorar
    - definir destino do backup
    - gera uma pasta no destino pra salvar o backup
    - gera um JSON na pasta do backup (no destino) pra salvar a config desse backup
    - tb salva a config do backup nos dados locais do nimbus (talvez no drive, se tiver ja?)
- Comandos de um Backup:
    - backup: copiar tudo dos sources, ignorando coisas de acordo, para a pasta de backup
    - restore: copia tudo do backup para seus locais de origem
    - diff: fazer diff entre sources e arquivos no backup pra ver quais diffs tem
        - deixar flag opcional pra mostrar diff entre arquivos de texto como git (se possivel)
        - no normal, só um "tais arquivos tem diff", e uns metadados tipo tamanho de cada um e data de criação/edit é suficiente
- Poder ter definição default de backup:
    - poder criar um backup a partir dessa config default pra poder ser editavel
    - sources:
        - ~/Downloads/ ???
        - ~/Documents/
        - ~/Imagens/ ???
        - ~/.ssh
        - TODO: verificar outras pastas pra isso


# Google Drive
- implementar suporte ao google drive
    - poder carregar/editar sheets (como fizemos na Tapps)
    - poder salvar/baixar arquivos direto no drive. Ai poderia usar tal API do drive como armazenamento remoto.
    - logar com sua conta google (nada de robot)
- com o drive, daria pra fazer backup direto dos dados do nimbus pro drive, e comando pra dar restore desse backup


# Outros
- talvez algumas funções relacionadas ao lcars-monitor?
- pensar em mais features uteis que poderia ter?