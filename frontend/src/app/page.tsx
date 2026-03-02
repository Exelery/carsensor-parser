"use client";

import { useEffect, useState, startTransition } from "react";
import { useRouter } from "next/navigation";
import {
  getToken,
  clearToken,
  getCars,
  getCarsCount,
  getRates,
  getFilterOptions,
  parseSearchQuery,
  ApiError,
  type Car,
  type CarsSortBy,
  type CarsOrder,
  type CarsFilters,
  type FilterOptions,
} from "@/lib/api";

const PAGE_SIZE = 20;

function ThSort({
  col,
  label,
  sortBy,
  order,
  onSort,
}: {
  col: CarsSortBy;
  label: string;
  sortBy: CarsSortBy;
  order: CarsOrder;
  onSort: (col: CarsSortBy) => void;
}) {
  return (
    <th
      className="cursor-pointer select-none px-4 py-3 font-medium text-zinc-900 dark:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-700"
      onClick={() => onSort(col)}
    >
      {label}
      {sortBy === col && <span className="ml-1">{order === "desc" ? "↓" : "↑"}</span>}
    </th>
  );
}

export default function Home() {
  const router = useRouter();
  const [cars, setCars] = useState<Car[]>([]);
  const [totalCount, setTotalCount] = useState<number | null>(null);
  const [jpyRub, setJpyRub] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState<CarsSortBy>("updated_at");
  const [order, setOrder] = useState<CarsOrder>("desc");
  const [filters, setFilters] = useState<CarsFilters>({});
  const [filterBrand, setFilterBrand] = useState("");
  const [filterYearMin, setFilterYearMin] = useState("");
  const [filterYearMax, setFilterYearMax] = useState("");
  const [filterPriceMin, setFilterPriceMin] = useState("");
  const [filterPriceMax, setFilterPriceMax] = useState("");
  const [filterBodyType, setFilterBodyType] = useState("");
  const [filterTransmission, setFilterTransmission] = useState("");
  const [filterSearch, setFilterSearch] = useState("");
  const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null);
  const [parsingSearch, setParsingSearch] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    let cancelled = false;
    startTransition(() => {
      setLoading(true);
      setError("");
    });
    const skip = (page - 1) * PAGE_SIZE;
    const params = {
      skip,
      limit: PAGE_SIZE,
      sort_by: sortBy,
      order,
      ...filters,
    };
    Promise.all([
      getCars(token, params),
      getCarsCount(token, filters),
      getRates(token),
    ])
      .then(([carsList, { total }, { jpy_rub }]) => {
        if (!cancelled) {
          setCars(carsList);
          setTotalCount(total);
          setJpyRub(jpy_rub);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) {
          clearToken();
          router.replace("/login");
          return;
        }
        setError("Не удалось загрузить список");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [router, page, sortBy, order, filters]);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    getFilterOptions(token)
      .then(setFilterOptions)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          clearToken();
          router.replace("/login");
        }
      });
  }, [router]);

  function handleLogout() {
    clearToken();
    router.replace("/login");
    router.refresh();
  }

  function handleSort(col: CarsSortBy) {
    if (sortBy === col) setOrder((o) => (o === "desc" ? "asc" : "desc"));
    else {
      setSortBy(col);
      setOrder("desc");
    }
    setPage(1);
  }

  async function applyFilters() {
    const token = getToken();
    if (!token) return;
    const next: CarsFilters = {};
    const searchTrim = filterSearch.trim();
    if (searchTrim) {
      setParsingSearch(true);
      try {
        const [parsed, rates] = await Promise.all([
          parseSearchQuery(token, searchTrim),
          getRates(token),
        ]);
        const hasParsed = parsed && Object.keys(parsed).length > 0;
        if (hasParsed) {
          if (parsed.brand != null && parsed.brand !== "") next.brand = parsed.brand;
          if (parsed.model != null && parsed.model !== "") next.model = parsed.model;
          if (parsed.color != null && parsed.color !== "") next.color = parsed.color;
          if (parsed.year_min != null) next.year_min = parsed.year_min;
          if (parsed.year_max != null) next.year_max = parsed.year_max;
          if (parsed.price_max_rub != null && parsed.price_max_rub > 0 && rates?.jpy_rub) {
            next.price_max = Math.round(parsed.price_max_rub / rates.jpy_rub);
          }
          if (parsed.transmission != null && parsed.transmission !== "") next.transmission = parsed.transmission;
          if (parsed.mileage_max_km != null) next.mileage_max_km = parsed.mileage_max_km;
          if (parsed.body_type != null && parsed.body_type !== "") next.body_type = parsed.body_type;
          if (parsed.drive_type != null && parsed.drive_type !== "") next.drive_type = parsed.drive_type;
          if (parsed.engine_type != null && parsed.engine_type !== "") next.engine_type = parsed.engine_type;
        } else {
          next.q = searchTrim;
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          clearToken();
          router.replace("/login");
          return;
        }
        throw err;
      } finally {
        setParsingSearch(false);
      }
    }
    if (filterBrand.trim()) next.brand = filterBrand.trim();
    if (filterYearMin !== "") {
      const n = parseInt(filterYearMin, 10);
      if (!Number.isNaN(n)) next.year_min = n;
    }
    if (filterYearMax !== "") {
      const n = parseInt(filterYearMax, 10);
      if (!Number.isNaN(n)) next.year_max = n;
    }
    if (filterPriceMin !== "") {
      const n = parseInt(filterPriceMin, 10);
      if (!Number.isNaN(n)) next.price_min = n;
    }
    if (filterPriceMax !== "") {
      const n = parseInt(filterPriceMax, 10);
      if (!Number.isNaN(n)) next.price_max = n;
    }
    if (filterBodyType.trim()) next.body_type = filterBodyType.trim();
    if (filterTransmission.trim()) next.transmission = filterTransmission.trim();
    setFilters(next);
    setPage(1);
  }

  function resetFilters() {
    setFilterSearch("");
    setFilterBrand("");
    setFilterYearMin("");
    setFilterYearMax("");
    setFilterPriceMin("");
    setFilterPriceMax("");
    setFilterBodyType("");
    setFilterTransmission("");
    setFilters({});
    setPage(1);
  }

  const totalPages = totalCount != null ? Math.max(1, Math.ceil(totalCount / PAGE_SIZE)) : 0;
  const token = typeof window !== "undefined" ? getToken() : null;
  if (token === null && !loading) return null;

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900">
      <header className="sticky top-0 z-10 border-b border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-800">
        <div className="mx-auto flex max-w-full items-center justify-between px-4 py-3">
          <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            Автообъявления
          </h1>
          <button
            type="button"
            onClick={handleLogout}
            className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
          >
            Выйти
          </button>
        </div>
      </header>
      <div className="flex">
        <aside className="sticky top-[53px] h-[calc(100vh-53px)] w-64 shrink-0 overflow-y-auto border-r border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-800">
          <div className="p-4">
            <h2 className="mb-3 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              Фильтры
            </h2>
            <div className="space-y-3">
              <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400">
                Поиск
              </label>
              <input
                type="search"
                value={filterSearch}
                onChange={(e) => setFilterSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && applyFilters()}
                placeholder="Марка, модель, цвет, заголовок..."
                className="w-full rounded border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-700 dark:text-zinc-100"
              />
              <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400">
                Марка
              </label>
              <select
                value={filterBrand}
                onChange={(e) => setFilterBrand(e.target.value)}
                className="w-full rounded border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-700 dark:text-zinc-100"
              >
                <option value="">—</option>
                {filterOptions?.brands.map((b) => (
                  <option key={b} value={b}>{b}</option>
                ))}
              </select>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400">
                    Год от
                  </label>
                  <input
                    type="number"
                    min={filterOptions?.year_min ?? 1990}
                    max={filterOptions?.year_max ?? 2030}
                    value={filterYearMin}
                    onChange={(e) => setFilterYearMin(e.target.value)}
                    placeholder={String(filterOptions?.year_min ?? "")}
                    className="w-full rounded border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-700 dark:text-zinc-100"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400">
                    Год до
                  </label>
                  <input
                    type="number"
                    min={filterOptions?.year_min ?? 1990}
                    max={filterOptions?.year_max ?? 2030}
                    value={filterYearMax}
                    onChange={(e) => setFilterYearMax(e.target.value)}
                    placeholder={String(filterOptions?.year_max ?? "")}
                    className="w-full rounded border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-700 dark:text-zinc-100"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400">
                  Цена (¥) от
                </label>
                <input
                  type="number"
                  min={filterOptions?.price_min ?? 0}
                  value={filterPriceMin}
                  onChange={(e) => setFilterPriceMin(e.target.value)}
                  placeholder={filterOptions != null ? String(filterOptions.price_min) : ""}
                  className="w-full rounded border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-700 dark:text-zinc-100"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400">
                  Цена (¥) до
                </label>
                <input
                  type="number"
                  min={filterOptions?.price_min ?? 0}
                  value={filterPriceMax}
                  onChange={(e) => setFilterPriceMax(e.target.value)}
                  placeholder={filterOptions != null ? String(filterOptions.price_max) : ""}
                  className="w-full rounded border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-700 dark:text-zinc-100"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400">
                  Кузов
                </label>
                <select
                  value={filterBodyType}
                  onChange={(e) => setFilterBodyType(e.target.value)}
                  className="w-full rounded border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-700 dark:text-zinc-100"
                >
                  <option value="">—</option>
                  {filterOptions?.body_types.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400">
                  КПП
                </label>
                <select
                  value={filterTransmission}
                  onChange={(e) => setFilterTransmission(e.target.value)}
                  className="w-full rounded border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-600 dark:bg-zinc-700 dark:text-zinc-100"
                >
                  <option value="">—</option>
                  {filterOptions?.transmissions.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => applyFilters()}
                  disabled={parsingSearch}
                  className="rounded border border-zinc-300 bg-zinc-100 px-3 py-1.5 text-sm hover:bg-zinc-200 disabled:opacity-60 dark:border-zinc-600 dark:bg-zinc-700 dark:hover:bg-zinc-600"
                >
                  {parsingSearch ? "Парсим…" : "Применить"}
                </button>
                <button
                  type="button"
                  onClick={resetFilters}
                  className="rounded border border-zinc-300 px-3 py-1.5 text-sm hover:bg-zinc-100 dark:border-zinc-600 dark:hover:bg-zinc-700"
                >
                  Сбросить
                </button>
              </div>
            </div>
          </div>
        </aside>
        <main className="min-w-0 flex-1 px-4 py-6">
          <div className="mb-4 flex gap-2">
            <input
              type="search"
              value={filterSearch}
              onChange={(e) => setFilterSearch(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && applyFilters()}
              placeholder="Поиск по марке, модели, цвету, заголовку..."
              className="max-w-md flex-1 rounded border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-600 dark:bg-zinc-700 dark:text-zinc-100"
            />
            <button
              type="button"
              onClick={() => applyFilters()}
              disabled={parsingSearch}
              className="shrink-0 rounded border border-zinc-300 bg-zinc-100 px-4 py-2 text-sm hover:bg-zinc-200 disabled:opacity-60 dark:border-zinc-600 dark:bg-zinc-700 dark:hover:bg-zinc-600"
            >
              {parsingSearch ? "Парсим…" : "Искать"}
            </button>
          </div>
        {loading && <p className="text-zinc-500">Загрузка…</p>}
        {error && <p className="text-red-600 dark:text-red-400">{error}</p>}
        {!loading && !error && totalCount !== null && (
          <p className="mb-4 text-zinc-600 dark:text-zinc-400">
            Всего в базе: <strong>{totalCount.toLocaleString("ru-RU")}</strong> авто
          </p>
        )}
        {!loading && !error && (
          <div className="overflow-x-auto rounded-lg border border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-800">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-700">
                  <ThSort col="brand" label="Марка" sortBy={sortBy} order={order} onSort={handleSort} />
                  <ThSort col="model" label="Модель" sortBy={sortBy} order={order} onSort={handleSort} />
                  <ThSort col="year" label="Год" sortBy={sortBy} order={order} onSort={handleSort} />
                  <ThSort col="total_price" label="Цена (¥)" sortBy={sortBy} order={order} onSort={handleSort} />
                  <th className="px-4 py-3 font-medium text-zinc-900 dark:text-zinc-100">Цена (₽)</th>
                  <th className="px-4 py-3 font-medium text-zinc-900 dark:text-zinc-100">Цвет</th>
                  <th className="px-4 py-3 font-medium text-zinc-900 dark:text-zinc-100">Трансмиссия</th>
                  <ThSort col="mileage_km" label="Пробег" sortBy={sortBy} order={order} onSort={handleSort} />
                  <ThSort col="body_type" label="Кузов" sortBy={sortBy} order={order} onSort={handleSort} />
                  <th className="max-w-[200px] px-4 py-3 font-medium text-zinc-900 dark:text-zinc-100">Заголовок</th>
                  <th className="px-4 py-3 font-medium text-zinc-900 dark:text-zinc-100">Ссылка</th>
                </tr>
              </thead>
              <tbody>
                {cars.map((c) => (
                  <tr
                    key={c.id}
                    className="border-b border-zinc-100 dark:border-zinc-700"
                  >
                    <td className="px-4 py-2 text-zinc-700 dark:text-zinc-300">
                      {c.brand}
                    </td>
                    <td className="px-4 py-2 text-zinc-700 dark:text-zinc-300">
                      {c.model}
                    </td>
                    <td className="px-4 py-2 text-zinc-700 dark:text-zinc-300">
                      {c.year}
                    </td>
                    <td className="px-4 py-2 text-zinc-700 dark:text-zinc-300">
                      {(c.total_price ?? c.price).toLocaleString("ru-RU")} ¥
                    </td>
                    <td className="px-4 py-2 text-zinc-700 dark:text-zinc-300">
                      {jpyRub != null
                        ? Math.round((c.total_price ?? c.price) * jpyRub).toLocaleString("ru-RU") + " ₽"
                        : "—"}
                    </td>
                    <td className="px-4 py-2 text-zinc-700 dark:text-zinc-300">
                      {c.color}
                    </td>
                    <td className="px-4 py-2 text-zinc-700 dark:text-zinc-300">
                      {c.transmission ?? "—"}
                    </td>
                    <td className="px-4 py-2 text-zinc-700 dark:text-zinc-300">
                      {c.mileage_display ?? (c.mileage_km != null ? `${(c.mileage_km / 1000).toFixed(1)} тыс. км` : "—")}
                    </td>
                    <td className="px-4 py-2 text-zinc-700 dark:text-zinc-300">
                      {c.body_type ?? "—"}
                    </td>
                    <td className="max-w-[200px] truncate px-4 py-2 text-zinc-700 dark:text-zinc-300" title={c.title ?? undefined}>
                      {c.title ?? "—"}
                    </td>
                    <td className="px-4 py-2">
                      <a
                        href={c.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline dark:text-blue-400"
                      >
                        Открыть
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {cars.length === 0 && !loading && (
              <p className="px-4 py-8 text-center text-zinc-500">
                Нет объявлений. Дождитесь обновления воркера.
              </p>
            )}
            {totalCount != null && totalCount > 0 && (
              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-zinc-200 px-4 py-3 dark:border-zinc-700">
                <span className="text-sm text-zinc-600 dark:text-zinc-400">
                  Страница {page} из {totalPages}
                  {totalCount != null && ` · всего ${totalCount.toLocaleString("ru-RU")}`}
                </span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={page <= 1 || loading}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    className="rounded border border-zinc-300 bg-white px-3 py-1.5 text-sm disabled:opacity-50 dark:border-zinc-600 dark:bg-zinc-700"
                  >
                    Назад
                  </button>
                  <button
                    type="button"
                    disabled={page >= totalPages || loading}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    className="rounded border border-zinc-300 bg-white px-3 py-1.5 text-sm disabled:opacity-50 dark:border-zinc-600 dark:bg-zinc-700"
                  >
                    Вперёд
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
        </main>
      </div>
    </div>
  );
}
