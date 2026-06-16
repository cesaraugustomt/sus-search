interface EmptyStateProps {
  query: string;
}

export function EmptyState({ query }: EmptyStateProps) {
  return (
    <div className="empty-state" role="status">
      <div className="empty-icon" aria-hidden="true">🔍</div>
      <h3 className="empty-title">Nenhum resultado encontrado</h3>
      <p className="empty-text">
        Não encontramos resultados para <strong>"{query}"</strong>.
      </p>
      <ul className="empty-tips">
        <li>Verifique a ortografia do termo</li>
        <li>Tente termos mais gerais (ex: "pneumonia" em vez de "pneumonia bacteriana")</li>
        <li>Remova o filtro de fonte para buscar em todas as bases</li>
        <li>Tente buscar pelo código diretamente (ex: "J18" ou "0301010013")</li>
      </ul>
    </div>
  );
}
