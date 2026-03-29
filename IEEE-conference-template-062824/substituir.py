import re

# Mapeamento completo das citações
citation_mapping = {
    'Maas2025': 'b1',
    'pedro__lvarez_ed947120': 'b2', 
    'tamara_dancheva_635e0512': 'b3',
    'lailan_m_haji_2b4efda5': 'b4',
    'zhonghong_ou_93958397': 'b5',
    'zhonghong_ou_2f9f325e': 'b6',
    'benjamin_farley_32066261': 'b7',
    'angeliki_katsenou_e0a9a00f': 'b8',
    'arnaldo_pereira_ferreira_bd8560e5': 'b9',
    'joel_scheuner_a07bc84e': 'b10',
    'sepideh_ebneyousef_1d5c43ab': 'b11',
    'tina_samizadeh_nikoui_765428f4': 'b12',
    'rumr2003': 'b13',
    'p__praveenchandar_6ddf409a': 'b14',
    'rosado2024coding': 'b15',
    'araujo2024fast': 'b16',
    'mahida-ankur': 'b17',
    'omar_alzakholi_0537f875': 'b18',
    'silva2025analise': 'b19',
    'jiang2025cloud': 'b20'
}

def replace_citations(file_path):
    """
    Substitui todas as citações no arquivo .tex usando o mapeamento
    """
    # Ler o arquivo
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Fazer as substituições
    original_content = content
    for old_cite, new_cite in citation_mapping.items():
        # Padrão para encontrar \cite{old_cite} ou \cite{old_cite, ...}
        pattern = r'\\cite\{(.*?' + re.escape(old_cite) + r'.*?)\}'
        
        def replace_match(match):
            inner_content = match.group(1)
            # Substituir apenas a chave específica, mantendo outras citações no mesmo \cite
            new_inner = re.sub(
                r'\b' + re.escape(old_cite) + r'\b', 
                new_cite, 
                inner_content
            )
            return f'\\cite{{{new_inner}}}'
        
        content = re.sub(pattern, replace_match, content)
    
    # Escrever o arquivo atualizado
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"✅ Substituições concluídas em: {file_path}")
        print(f"📊 Total de citações substituídas: {len(citation_mapping)}")
    else:
        print("ℹ️  Nenhuma substituição foi necessária.")

def preview_changes(file_path):
    """
    Mostra preview das mudanças sem salvar
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    print("🔍 PREVIEW das mudanças:")
    print("-" * 50)
    
    for old_cite, new_cite in citation_mapping.items():
        pattern = r'\\cite\{(.*?' + re.escape(old_cite) + r'.*?)\}'
        matches = re.findall(pattern, content)
        
        if matches:
            for match in matches:
                old_full = f'\\cite{{{match}}}'
                new_inner = re.sub(r'\b' + re.escape(old_cite) + r'\b', new_cite, match)
                new_full = f'\\cite{{{new_inner}}}'
                print(f"  {old_full} → {new_full}")

# USO:
if __name__ == "__main__":
    # Nome do seu arquivo .tex
    tex_file = "noms.tex"  # 👈 ALTERE AQUI com o nome do seu arquivo
    
    # 1. Primeiro veja o que será alterado
    preview_changes(tex_file)
    
    # 2. Confirme antes de aplicar
    resposta = input("\n❓ Aplicar as mudanças? (s/n): ")
    if resposta.lower() == 's':
        replace_citations(tex_file)
    else:
        print("Operação cancelada.")
