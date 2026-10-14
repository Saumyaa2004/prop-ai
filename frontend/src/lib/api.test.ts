import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, buildSearchQuery, getProperty, searchProperties } from "@/lib/api";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("buildSearchQuery", () => {
  it("always includes listing_type", () => {
    expect(buildSearchQuery({ listing_type: "rent" }).toString()).toBe("listing_type=rent");
  });

  it("leaves out filters that are not set", () => {
    const query = buildSearchQuery({
      listing_type: "sale",
      locality: "",
      bedrooms: undefined,
      max_price: 15_000_000,
    });

    expect(query.toString()).toBe("listing_type=sale&max_price=15000000");
  });

  it("repeats list filters the way FastAPI expects", () => {
    const query = buildSearchQuery({ listing_type: "sale", amenities: ["parking", "gym"] });

    expect(query.getAll("amenities")).toEqual(["parking", "gym"]);
  });

  it("keeps zero values, e.g. studios have 0 bedrooms", () => {
    expect(buildSearchQuery({ listing_type: "rent", bedrooms: 0 }).get("bedrooms")).toBe("0");
  });
});

describe("searchProperties", () => {
  it("calls the search endpoint and returns the parsed body", async () => {
    const body = { count: 0, results: [] };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(body));
    vi.stubGlobal("fetch", fetchMock);

    const result = await searchProperties({ listing_type: "rent", locality: "Powai" });

    expect(result).toEqual(body);
    const calledUrl = new URL(fetchMock.mock.calls[0][0]);
    expect(calledUrl.pathname).toBe("/properties/search");
    expect(calledUrl.searchParams.get("listing_type")).toBe("rent");
    expect(calledUrl.searchParams.get("locality")).toBe("Powai");
  });

  it("turns a 422 into an ApiError with a readable message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ detail: [{ type: "missing" }] }, 422))
    );

    const error = await searchProperties({ listing_type: "sale" }).catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(422);
    expect(error.message).toBe("Some search filters are invalid.");
  });

  it("uses the API's message when detail is a string", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ detail: "Property not found" }, 404))
    );

    await expect(searchProperties({ listing_type: "sale" })).rejects.toMatchObject({
      status: 404,
      message: "Property not found",
    });
  });

  it("reports an unreachable backend as status 0", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(searchProperties({ listing_type: "sale" })).rejects.toMatchObject({
      name: "ApiError",
      status: 0,
    });
  });

  it("re-throws cancellations instead of reporting an error", async () => {
    const controller = new AbortController();
    controller.abort();
    const abortError = new DOMException("Aborted", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abortError));

    await expect(
      searchProperties({ listing_type: "sale" }, { signal: controller.signal })
    ).rejects.toBe(abortError);
  });
});

describe("getProperty", () => {
  it("requests one listing by code", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ listing_code: "PAI-DEMO-002" }));
    vi.stubGlobal("fetch", fetchMock);

    const listing = await getProperty("PAI-DEMO-002");

    expect(listing.listing_code).toBe("PAI-DEMO-002");
    expect(new URL(fetchMock.mock.calls[0][0]).pathname).toBe("/properties/PAI-DEMO-002");
  });

  it("encodes the code so it cannot change which endpoint is called", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}));
    vi.stubGlobal("fetch", fetchMock);

    await getProperty("../health");

    expect(fetchMock.mock.calls[0][0]).toContain("/properties/..%2Fhealth");
  });

  it("rejects with status 404 for an unknown code", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ detail: "Property not found" }, 404))
    );

    await expect(getProperty("PAI-DEMO-999")).rejects.toMatchObject({
      status: 404,
      message: "Property not found",
    });
  });
});
