import { describe, it, expect, vi, beforeEach } from "vitest";
import { searchTerms, fetchSources, fetchHealth } from "../../src/services/api";

// ── Mock global fetch
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

const makeOkResponse = (data: unknown) => ({
  ok: true,
  json: () => Promise.resolve(data),
});

const makeErrResponse = (status: number, msg = "") => ({
  ok: false,
  status,
  statusText: msg || "Error",
  text: () => Promise.resolve(msg),
});

const mockSearchResult = {
  query: "pneumonia",
  total: 1,
  page: 1,
  limit: 20,
  pages: 1,
  results: [
    {
      id: 1,
      code: "J18.9",
      name: "PNEUMONIA NÃO ESPECIFICADA",
      description: null,
      source: "CID10",
      category: "CID",
      subcategory: null,
      additional_info: {},
      official_url: "https://rts.saude.gov.br",
      source_competency: "04/2025",
      last_updated: null,
      created_at: null,
    },
  ],
};

describe("searchTerms()", () => {
  beforeEach(() => mockFetch.mockReset());

  it("chama /api/v1/search com o parâmetro q correto", async () => {
    mockFetch.mockResolvedValue(makeOkResponse(mockSearchResult));
    await searchTerms({ q: "pneumonia" });
    const url: string = mockFetch.mock.calls[0][0].toString();
    expect(url).toContain("/api/v1/search");
    expect(url).toContain("q=pneumonia");
  });

  it("inclui parâmetro page e limit", async () => {
    mockFetch.mockResolvedValue(makeOkResponse(mockSearchResult));
    await searchTerms({ q: "consulta", page: 2, limit: 10 });
    const url: string = mockFetch.mock.calls[0][0].toString();
    expect(url).toContain("page=2");
    expect(url).toContain("limit=10");
  });

  it("inclui parâmetro source quando fornecido", async () => {
    mockFetch.mockResolvedValue(makeOkResponse(mockSearchResult));
    await searchTerms({ q: "consulta", source: "SIGTAP" });
    const url: string = mockFetch.mock.calls[0][0].toString();
    expect(url).toContain("source=SIGTAP");
  });

  it("não inclui source quando vazio", async () => {
    mockFetch.mockResolvedValue(makeOkResponse(mockSearchResult));
    await searchTerms({ q: "consulta", source: "" });
    const url: string = mockFetch.mock.calls[0][0].toString();
    expect(url).not.toContain("source=");
  });

  it("retorna os dados corretamente", async () => {
    mockFetch.mockResolvedValue(makeOkResponse(mockSearchResult));
    const result = await searchTerms({ q: "pneumonia" });
    expect(result.total).toBe(1);
    expect(result.results[0].code).toBe("J18.9");
  });

  it("lança erro quando status não é 2xx", async () => {
    mockFetch.mockResolvedValue(makeErrResponse(422, "Validation error"));
    await expect(searchTerms({ q: "x" })).rejects.toThrow("API 422");
  });

  it("lança erro em falha de rede", async () => {
    mockFetch.mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(searchTerms({ q: "consulta" })).rejects.toThrow();
  });
});

describe("fetchSources()", () => {
  beforeEach(() => mockFetch.mockReset());

  it("chama /api/v1/sources", async () => {
    mockFetch.mockResolvedValue(makeOkResponse([]));
    await fetchSources();
    expect(mockFetch.mock.calls[0][0].toString()).toContain("/api/v1/sources");
  });

  it("retorna array de fontes", async () => {
    const sources = [
      { code: "SIGTAP", name: "SIGTAP", record_count: 4600 },
      { code: "CID10", name: "CID-10", record_count: 15000 },
    ];
    mockFetch.mockResolvedValue(makeOkResponse(sources));
    const result = await fetchSources();
    expect(result).toHaveLength(2);
    expect(result[0].code).toBe("SIGTAP");
  });
});

describe("fetchHealth()", () => {
  beforeEach(() => mockFetch.mockReset());

  it("retorna status e total de termos", async () => {
    mockFetch.mockResolvedValue(
      makeOkResponse({ status: "ok", version: "1.0.0", database: "ok", total_terms: 20000 })
    );
    const result = await fetchHealth();
    expect(result.status).toBe("ok");
    expect(result.total_terms).toBe(20000);
  });
});
