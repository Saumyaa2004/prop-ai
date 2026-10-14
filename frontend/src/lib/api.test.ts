import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  bookVisit,
  buildSearchQuery,
  getProperty,
  getSlots,
  searchProperties,
  sendChat,
} from "@/lib/api";

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

describe("sendChat", () => {
  it("posts the conversation as JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ reply: "Hi", listings: [] }));
    vi.stubGlobal("fetch", fetchMock);
    const messages = [{ role: "user" as const, content: "flats in Powai" }];

    const result = await sendChat(messages);

    expect(result.reply).toBe("Hi");
    const [url, init] = fetchMock.mock.calls[0];
    expect(new URL(url).pathname).toBe("/chat");
    expect(init.method).toBe("POST");
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(init.body)).toEqual({ messages });
  });

  it("passes the backend's 503 message through to the user", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ detail: "The AI assistant is temporarily unavailable. Please try again." }, 503)
      )
    );

    await expect(sendChat([{ role: "user", content: "hi" }])).rejects.toMatchObject({
      status: 503,
      message: "The AI assistant is temporarily unavailable. Please try again.",
    });
  });

  it("reports an unreachable backend as status 0", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(sendChat([{ role: "user", content: "hi" }])).rejects.toMatchObject({ status: 0 });
  });
});

describe("visits API", () => {
  it("asks for one day's slots", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ listing_code: "PAI-DEMO-002", slots: [] }));
    vi.stubGlobal("fetch", fetchMock);

    await getSlots("PAI-DEMO-002", "2026-10-18");

    expect(fetchMock.mock.calls[0][0]).toBe(
      "http://localhost:8000/properties/PAI-DEMO-002/slots?date=2026-10-18"
    );
  });

  it("asks for all slots when no day is given", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ listing_code: "PAI-DEMO-002", slots: [] }));
    vi.stubGlobal("fetch", fetchMock);

    await getSlots("PAI-DEMO-002");

    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/properties/PAI-DEMO-002/slots");
  });

  it("books a visit with a JSON POST", async () => {
    const visit = {
      id: 7,
      listing_code: "PAI-DEMO-002",
      title: "Hiranandani Gardens 2BHK",
      starts_at: "2026-10-18T11:00:00+05:30",
      status: "booked",
    };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(visit, 201));
    vi.stubGlobal("fetch", fetchMock);
    const request = {
      listing_code: "PAI-DEMO-002",
      starts_at: "2026-10-18T11:00:00+05:30",
      name: "Asha Demo",
      phone: "98765 43210",
    };

    await expect(bookVisit(request)).resolves.toEqual(visit);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://localhost:8000/visits");
    expect(init.method).toBe("POST");
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(init.body)).toEqual(request);
  });

  it("passes the backend's 409 message to the user", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ detail: "Sorry, that slot was just taken." }, 409))
    );

    const error = await bookVisit({
      listing_code: "PAI-DEMO-002",
      starts_at: "2026-10-18T11:00:00+05:30",
      name: "Asha Demo",
      phone: "98765 43210",
    }).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(409);
    expect((error as ApiError).message).toBe("Sorry, that slot was just taken.");
  });
});
