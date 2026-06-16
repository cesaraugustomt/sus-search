import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ResultCard } from "../../src/components/ResultCard";
import type { Term } from "../../src/types";

const base: Term = {
  id: 1,
  code: "J18.9",
  name: "PNEUMONIA NÃO ESPECIFICADA",
  description: "Infecção pulmonar de etiologia não determinada",
  source: "CID10",
  category: "Classificação Internacional de Doenças",
  subcategory: null,
  additional_info: {},
  official_url: "https://rts.saude.gov.br",
  source_competency: "04/2025",
  last_updated: null,
  created_at: null,
};

describe("ResultCard", () => {
  it("renderiza o nome do termo", () => {
    render(<ResultCard term={base} />);
    expect(screen.getByText("PNEUMONIA NÃO ESPECIFICADA")).toBeInTheDocument();
  });

  it("renderiza o código quando disponível", () => {
    render(<ResultCard term={base} />);
    expect(screen.getByText("J18.9")).toBeInTheDocument();
  });

  it("renderiza o badge CID-10 para termos CID10", () => {
    render(<ResultCard term={base} />);
    expect(screen.getByText("CID-10")).toBeInTheDocument();
  });

  it("renderiza badge SIGTAP para procedimentos", () => {
    render(<ResultCard term={{ ...base, source: "SIGTAP" }} />);
    expect(screen.getByText("SIGTAP")).toBeInTheDocument();
  });

  it("renderiza badge CNES para estabelecimentos", () => {
    render(<ResultCard term={{ ...base, source: "CNES" }} />);
    expect(screen.getByText("CNES")).toBeInTheDocument();
  });

  it("exibe a descrição quando fornecida", () => {
    render(<ResultCard term={base} />);
    expect(screen.getByText("Infecção pulmonar de etiologia não determinada")).toBeInTheDocument();
  });

  it("não exibe descrição quando null", () => {
    render(<ResultCard term={{ ...base, description: null }} />);
    expect(
      screen.queryByText("Infecção pulmonar de etiologia não determinada")
    ).not.toBeInTheDocument();
  });

  it("não exibe código quando null", () => {
    render(<ResultCard term={{ ...base, code: null }} />);
    expect(screen.queryByText("J18.9")).not.toBeInTheDocument();
  });

  it("link aponta para a URL oficial com target blank", () => {
    render(<ResultCard term={base} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "https://rts.saude.gov.br");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("não renderiza link quando official_url é null", () => {
    render(<ResultCard term={{ ...base, official_url: null }} />);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("exibe a competência quando disponível", () => {
    render(<ResultCard term={base} />);
    expect(screen.getByText("04/2025")).toBeInTheDocument();
  });

  it("exibe a categoria quando disponível", () => {
    render(<ResultCard term={base} />);
    expect(screen.getByText(/Classificação Internacional/)).toBeInTheDocument();
  });
});
