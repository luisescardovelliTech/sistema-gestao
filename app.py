import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime
import pytz

# --- Configurações de Página ---
st.set_page_config(page_title="Sistema Gestao", layout="wide", page_icon="🚀")
FUSO_HORARIO = pytz.timezone('America/Sao_Paulo')

# --- Conexão com Supabase ---
def init_connection():
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        database=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASS"],
        port=st.secrets["DB_PORT"]
    )

# --- FUNÇÕES: GESTÃO DE TIME ---
def carregar_equipe():
    conn = init_connection()
    df = pd.read_sql("SELECT nome FROM funcionarios WHERE ativo = TRUE ORDER BY nome", conn)
    conn.close()
    lista = ["Selecione seu nome"] + df['nome'].tolist()
    return lista

def adicionar_funcionario(novo_nome):
    conn = init_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO funcionarios (nome) VALUES (%s)", (novo_nome,))
        conn.commit()
        sucesso = True
    except:
        sucesso = False
    conn.close()
    return sucesso

def remover_funcionario(nome):
    conn = init_connection()
    c = conn.cursor()
    c.execute("UPDATE funcionarios SET ativo = FALSE WHERE nome = %s", (nome,))
    conn.commit()
    conn.close()

# --- FUNÇÕES: REGISTROS E DAILY ---
def registrar_acao(funcionario, projeto, etapa, tipo_acao, obs):
    conn = init_connection()
    c = conn.cursor()
    agora = datetime.now(FUSO_HORARIO)
    query = """
        INSERT INTO registro_ponto (funcionario, projeto, etapa, tipo_acao, timestamp, observacao)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    c.execute(query, (funcionario, projeto, etapa, tipo_acao, agora, obs))
    conn.commit()
    conn.close()

def registrar_daily(funcionario, fez_ontem, fara_hoje, dificuldades):
    conn = init_connection()
    c = conn.cursor()
    hoje = datetime.now(FUSO_HORARIO).strftime("%Y-%m-%d")
    c.execute("SELECT id FROM daily_scrum WHERE funcionario = %s AND data_registro = %s", (funcionario, hoje))
    if c.fetchone():
        conn.close()
        return False
    query = """
        INSERT INTO daily_scrum (funcionario, data_registro, fez_ontem, fara_hoje, dificuldades)
        VALUES (%s, %s, %s, %s, %s)
    """
    c.execute(query, (funcionario, hoje, fez_ontem, fara_hoje, dificuldades))
    conn.commit()
    conn.close()
    return True

# --- FUNÇÕES: ADMIN (CRUD) ---
def ler_registros():
    conn = init_connection()
    df = pd.read_sql("SELECT * FROM registro_ponto ORDER BY id DESC", conn)
    conn.close()
    
    # Converter timestamp para horário de Brasília e formatar dd/mm/aaaa hh:mm
    if not df.empty and 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        df['timestamp'] = df['timestamp'].dt.tz_convert(FUSO_HORARIO)
        df['timestamp'] = df['timestamp'].dt.strftime('%d/%m/%Y %H:%M')
    
    return df

def excluir_registro(id_registro):
    conn = init_connection()
    c = conn.cursor()
    c.execute("DELETE FROM registro_ponto WHERE id = %s", (id_registro,))
    conn.commit()
    conn.close()

def editar_registro(id_registro, novo_projeto, nova_observacao):
    conn = init_connection()
    c = conn.cursor()
    query = "UPDATE registro_ponto SET projeto = %s, observacao = %s WHERE id = %s"
    c.execute(query, (novo_projeto, nova_observacao, id_registro))
    conn.commit()
    conn.close()

def ler_daily_hoje():
    conn = init_connection()
    df = pd.read_sql("SELECT * FROM daily_scrum", conn)
    conn.close()
    hoje = datetime.now(FUSO_HORARIO).strftime("%Y-%m-%d")
    if not df.empty:
        df['data_registro'] = pd.to_datetime(df['data_registro']).dt.strftime("%Y-%m-%d")
        df = df[df['data_registro'] == hoje]
    return df

# --- Interface Principal ---
def main():
    st.sidebar.title("Navegação")
    OPCAO_DEV = "👷 Área do Dev"
    OPCAO_ADMIN = "👮 Área do Admin"
    
    equipe_dinamica = carregar_equipe()
    
    modo = st.sidebar.radio("Ir para:", [OPCAO_DEV, OPCAO_ADMIN])

    # ==========================
    # ÁREA DO FUNCIONÁRIO
    # ==========================
    if modo == OPCAO_DEV:
        st.title("Painel do Desenvolvedor")
        tab_registro, tab_daily = st.tabs(["⏱️ Registrar Atividade", "📋 Preencher Daily"])
        
        with tab_registro:
            col1, col2 = st.columns([1, 2])
            with col1:
                with st.form("form_registro", clear_on_submit=True):
                    st.subheader("O que você está fazendo?")
                    func_ponto = st.selectbox("Seu Nome", equipe_dinamica)
                    projeto = st.text_input("Projeto / Cliente")
                    etapa = st.selectbox("Tipo da Tarefa", ["Raspagem", "Tratamento de Dados", "Upload/Entrega", "Correção/Bug", "Reunião"])
                    obs = st.text_input("Detalhes (Opcional)")
                    
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("▶️ INICIAR Tarefa"):
                        if func_ponto != "Selecione seu nome":
                            registrar_acao(func_ponto, projeto, etapa, "INICIO", obs)
                            st.success(f"Início de {etapa} registrado!")
                        else:
                            st.error("Selecione seu nome.")
                    
                    if c2.form_submit_button("⏹️ CONCLUIR Tarefa"):
                        if func_ponto != "Selecione seu nome":
                            registrar_acao(func_ponto, projeto, etapa, "FIM", obs)
                            st.warning(f"Fim de {etapa} registrado!")
                        else:
                            st.error("Selecione seu nome.")

        with tab_daily:
            st.markdown("### 📢 Daily Scrum")
            with st.form("form_daily"):
                func_daily = st.selectbox("Seu Nome", equipe_dinamica, key="daily_user")
                c1, c2 = st.columns(2)
                ontem = c1.text_area("1. O que fiz ontem?", height=100)
                hoje = c2.text_area("2. O que farei hoje?", height=100)
                st.markdown("**3. Existe algum impedimento?**")
                impedimento = st.text_area("Impedimento", height=80, label_visibility="collapsed")
                
                if st.form_submit_button("🚀 Enviar Update"):
                    if func_daily != "Selecione seu nome":
                        if registrar_daily(func_daily, ontem, hoje, impedimento):
                            st.balloons()
                            st.success("Update enviado!")
                        else:
                            st.error("Já enviado hoje.")
                    else:
                        st.error("Selecione nome.")

    # ==========================
    # ÁREA DO GESTOR
    # ==========================
    elif modo == OPCAO_ADMIN:
        st.title("Centro de Comando")
        senha = st.sidebar.text_input("Senha Admin", type="password")
        
        if senha == st.secrets["ADMIN_PASS"]:
            st.success("Acesso Concedido")
            tab_daily, tab_hist, tab_team = st.tabs(["📢 Visão Daily", "🛠️ Gerenciar Registros", "👥 Gerenciar Time"])
            
            # --- DAILY ---
            with tab_daily:
                if st.button("🔄 Atualizar"): st.rerun()
                df_daily = ler_daily_hoje()
                if not df_daily.empty:
                    for _, row in df_daily.iterrows():
                        problema = len(str(row['dificuldades'])) > 3
                        cor = "🔴" if problema else "🟢"
                        with st.expander(f"{cor} {row['funcionario']}", expanded=problema):
                            st.write(f"**Ontem:** {row['fez_ontem']}")
                            st.write(f"**Hoje:** {row['fara_hoje']}")
                            if problema: st.error(f"**Bloqueio:** {row['dificuldades']}")
                            else: st.success("Sem bloqueios")
                else:
                    st.info("Nenhum update hoje.")

            # --- CRUD REGISTROS ---
            with tab_hist:
                st.subheader("Histórico de Atividades")
                
                # Carregar registros
                df_registros = ler_registros()
                
                if not df_registros.empty:
                    # --- FILTROS ---
                    st.markdown("### 🔍 Filtros de Busca")
                    col_f1, col_f2, col_f3 = st.columns(3)
                    
                    with col_f1:
                        funcionarios_unicos = ["Todos"] + sorted(df_registros['funcionario'].unique().tolist())
                        filtro_func = st.selectbox("Filtrar por Funcionário", funcionarios_unicos)
                    
                    with col_f2:
                        projetos_unicos = ["Todos"] + sorted(df_registros['projeto'].unique().tolist())
                        filtro_proj = st.selectbox("Filtrar por Projeto", projetos_unicos)
                    
                    with col_f3:
                        if st.button("🔄 Limpar Filtros"):
                            st.rerun()
                    
                    # Aplicar filtros
                    df_filtrado = df_registros.copy()
                    if filtro_func != "Todos":
                        df_filtrado = df_filtrado[df_filtrado['funcionario'] == filtro_func]
                    if filtro_proj != "Todos":
                        df_filtrado = df_filtrado[df_filtrado['projeto'] == filtro_proj]
                    
                    st.info(f"📊 Exibindo **{len(df_filtrado)}** de **{len(df_registros)}** registros. **Selecione uma linha para editar ou excluir.**")
                    
                    # Tabela com Seleção
                    event = st.dataframe(
                        df_filtrado,
                        on_select="rerun",
                        selection_mode="single-row",
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    # Lógica de Seleção
                    if event.selection.rows:
                        idx_selecionado = event.selection.rows[0]
                        registro_selecionado = df_filtrado.iloc[idx_selecionado]
                        # CORREÇÃO: Converter numpy.int64 para int nativo do Python
                        id_sel = int(registro_selecionado['id'])
                        
                        st.divider()
                        st.markdown(f"### 👉 Registro Selecionado: ID {id_sel}")
                        
                        col_edit, col_del = st.columns(2)
                        
                        # --- EDITAR ---
                        with col_edit:
                            with st.expander("✏️ **Editar Registro**", expanded=True):
                                with st.form(f"edit_form_{id_sel}"):
                                    novo_proj = st.text_input("Projeto", value=registro_selecionado['projeto'])
                                    nova_obs = st.text_input("Observação", value=registro_selecionado['observacao'])
                                    if st.form_submit_button("💾 Salvar Alterações"):
                                        editar_registro(id_sel, novo_proj, nova_obs)
                                        st.success("✅ Atualizado com sucesso!")
                                        st.rerun()
                        
                        # --- EXCLUIR ---
                        with col_del:
                            with st.expander("🗑️ **Excluir Registro**", expanded=True):
                                with st.form(f"del_form_{id_sel}"):
                                    st.warning(f"Tem certeza que deseja excluir o registro de **{registro_selecionado['funcionario']}**?")
                                    confirmacao = st.text_input("Digite 'CONFIRMAR' para excluir", type="default")
                                    if st.form_submit_button("⚠️ Excluir Definitivamente"):
                                        if confirmacao.upper() == "CONFIRMAR":
                                            excluir_registro(id_sel)
                                            st.success("✅ Registro excluído!")
                                            st.rerun()
                                        else:
                                            st.error("❌ Digite 'CONFIRMAR' corretamente.")

                else:
                    st.info("Nenhum registro encontrado.")

            # --- GESTÃO TIME ---
            with tab_team:
                st.subheader("Gestão de Acessos")
                col_add, col_rem = st.columns(2)
                
                with col_add:
                    with st.form("add_dev"):
                        novo_nome = st.text_input("Nome do Colaborador")
                        if st.form_submit_button("Adicionar"):
                            if novo_nome:
                                if adicionar_funcionario(novo_nome):
                                    st.success(f"{novo_nome} adicionado!")
                                    st.rerun()
                                else:
                                    st.error("Nome já existe.")
                
                with col_rem:
                    with st.form("rem_dev"):
                        lista_remocao = [x for x in equipe_dinamica if x != "Selecione seu nome"]
                        nome_rem = st.selectbox("Revogar Acesso", lista_remocao)
                        if st.form_submit_button("Revogar"):
                            remover_funcionario(nome_rem)
                            st.warning(f"Acesso de {nome_rem} revogado.")
                            st.rerun()

        elif senha:
            st.error("Senha Incorreta")

if __name__ == '__main__':
    main()