/**
 * BLOCK V2-20: Recently Viewed Products
 * Shows products user has viewed from localStorage
 */
import React, { useEffect, useState } from "react";
import { Clock, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import ProductCard from "../ProductCard";

const API_URL = process.env.REACT_APP_BACKEND_URL;

function extractProductId(value) {
  if (!value) return null;
  if (typeof value === "string" || typeof value === "number")
    return String(value);
  if (typeof value === "object") {
    if (value.id != null) return String(value.id);
    if (value._id != null) return String(value._id);
  }
  return null;
}

export default function RecentlyViewed() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const raw = JSON.parse(localStorage.getItem("recentlyViewed") || "[]");
    const ids = raw.map(extractProductId).filter(Boolean);

    if (!ids.length) {
      setLoading(false);
      return;
    }

    // Fetch products by IDs через существующий endpoint /api/products/{id}
    Promise.all(
      ids.slice(0, 8).map((id) =>
        fetch(`${API_URL}/api/products/${id}`)
          .then((r) => (r.ok ? r.json() : null))
          .catch(() => null),
      ),
    )
      .then((products) => {
        const resolved = products.filter(Boolean);
        if (resolved.length) {
          setItems(resolved);
          setLoading(false);
          return;
        }

        // Fallback - just show from catalog
        fetch(`${API_URL}/api/v2/catalog?limit=4`)
          .then((r) => r.json())
          .then((d) => {
            setItems(d.products || d.items || []);
            setLoading(false);
          })
          .catch(() => setLoading(false));
      })
      .catch(() => {
        fetch(`${API_URL}/api/v2/catalog?limit=4`)
          .then((r) => r.json())
          .then((d) => {
            setItems(d.products || d.items || []);
            setLoading(false);
          })
          .catch(() => setLoading(false));
      });
  }, []);

  if (loading || !items.length) return null;

  return (
    <div data-testid="recently-viewed" className="my-12 sm:my-16">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl sm:text-2xl font-bold flex items-center gap-3">
          <Clock className="w-6 h-6 text-gray-500" />
          Ви переглядали
        </h2>
        <Link
          to="/catalog"
          className="text-blue-600 font-semibold flex items-center gap-1 hover:gap-2 transition-all"
        >
          Весь каталог <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      {/* Products Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6">
        {items.map((product) => (
          <ProductCard key={product.id || product._id} product={product} />
        ))}
      </div>
    </div>
  );
}

// Helper function to add product to recently viewed
export function addToRecentlyViewed(productId) {
  const normalizedId = extractProductId(productId);
  if (!normalizedId) return;

  let viewed = JSON.parse(localStorage.getItem("recentlyViewed") || "[]");
  viewed = viewed
    .map(extractProductId)
    .filter(Boolean)
    .filter((id) => id !== normalizedId);
  viewed.unshift(normalizedId);
  viewed = viewed.slice(0, 12);
  localStorage.setItem("recentlyViewed", JSON.stringify(viewed));
}
