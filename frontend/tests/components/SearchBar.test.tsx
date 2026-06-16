import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SearchBar } from "../../src/components/SearchBar";

describe("SearchBar", () => {
  it("renderiza o campo de busca e o botão", () => {
    render(<SearchBar onSearch={vi.fn()} />);
    expect(screen.getByRole("searchbox")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /buscar/i })).toBeInTheDocument();
  });

  it("botão desabilitado quando query tem menos de 2 chars", () => {
    render(<SearchBar onSearch={vi.fn()} />);
    expect(screen.getByRole("button", { name: /buscar/i })).toBeDisabled();
  });

  it("botão habilitado quando query tem 2+ chars", async () => {
    const user = userEvent.setup();
    render(<SearchBar onSearch={vi.fn()} />);
    await user.type(screen.getByRole("searchbox"), "ab");
    expect(screen.getByRole("button", { name: /buscar/i })).not.toBeDisabled();
  });

  it("chama onSearch com o termo correto ao submeter", async () => {
    const user = userEvent.setup();
    const onSearch = vi.fn();
    render(<SearchBar onSearch={onSearch} />);
    await user.type(screen.getByRole("searchbox"), "pneumonia");
    await user.click(screen.getByRole("button", { name: /buscar/i }));
    expect(onSearch).toHaveBeenCalledWith("pneumonia");
    expect(onSearch).toHaveBeenCalledTimes(1);
  });

  it("não chama onSearch quando query é muito curta", async () => {
    const user = userEvent.setup();
    const onSearch = vi.fn();
    render(<SearchBar onSearch={onSearch} />);
    await user.type(screen.getByRole("searchbox"), "a");
    await user.keyboard("{Enter}");
    expect(onSearch).not.toHaveBeenCalled();
  });

  it("trim: remove espaços antes de chamar onSearch", async () => {
    const user = userEvent.setup();
    const onSearch = vi.fn();
    render(<SearchBar onSearch={onSearch} />);
    await user.type(screen.getByRole("searchbox"), "  consulta  ");
    await user.click(screen.getByRole("button", { name: /buscar/i }));
    expect(onSearch).toHaveBeenCalledWith("consulta");
  });

  it("exibe botão limpar quando há texto digitado", async () => {
    const user = userEvent.setup();
    render(<SearchBar onSearch={vi.fn()} />);
    await user.type(screen.getByRole("searchbox"), "teste");
    expect(screen.getByLabelText(/limpar/i)).toBeInTheDocument();
  });

  it("limpa o campo ao clicar no botão ×", async () => {
    const user = userEvent.setup();
    render(<SearchBar onSearch={vi.fn()} />);
    await user.type(screen.getByRole("searchbox"), "teste");
    await user.click(screen.getByLabelText(/limpar/i));
    expect(screen.getByRole("searchbox")).toHaveValue("");
  });

  it("exibe estado carregando no botão", () => {
    render(<SearchBar onSearch={vi.fn()} loading={true} />);
    const btn = screen.getByRole("button", { name: /buscando/i });
    expect(btn).toBeDisabled();
  });

  it("inicializa com valor inicial quando passado", () => {
    render(<SearchBar onSearch={vi.fn()} initialValue="hipertensão" />);
    expect(screen.getByRole("searchbox")).toHaveValue("hipertensão");
  });
});
