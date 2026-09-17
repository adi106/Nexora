import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { listCategories } from "../../api/categories";
import { getMyProduct } from "../../api/sellers";
import {
  createProduct,
  createVariant,
  setProductActive,
  setVariantActive,
  updateInventory,
  updateProductDetails,
  updateVariantDetails,
} from "../../api/sellerCatalog";
import { getInventory } from "../../api/inventory";
import { LoadingSpinner } from "../../components/LoadingSpinner";
import { ErrorMessage } from "../../components/ErrorMessage";
import { extractErrorMessage } from "../../api/client";
import type { Category, ProductDetail, ProductVariant } from "../../types";

function parseAttributes(input: string): Record<string, string> {
  const attributes: Record<string, string> = {};
  input
    .split(",")
    .map((pair) => pair.trim())
    .filter(Boolean)
    .forEach((pair) => {
      const [key, ...rest] = pair.split(":");
      if (key && rest.length > 0) {
        attributes[key.trim()] = rest.join(":").trim();
      }
    });
  return attributes;
}

export function SellerProductFormPage() {
  const { productId } = useParams<{ productId: string }>();
  const navigate = useNavigate();
  const isEditing = Boolean(productId);

  const [categories, setCategories] = useState<Category[]>([]);
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [basePrice, setBasePrice] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [isLoading, setIsLoading] = useState(isEditing);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listCategories().then(setCategories).catch(() => setCategories([]));
  }, []);

  function loadProduct() {
    if (!productId) return;
    setIsLoading(true);
    getMyProduct(productId)
      .then((data) => {
        setProduct(data);
        setName(data.name);
        setSlug(data.slug);
        setDescription(data.description ?? "");
        setBasePrice(String(data.base_price));
        setCategoryId(String(data.category_id));
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setIsLoading(false));
  }

  useEffect(loadProduct, [productId]);

  async function handleSaveProduct(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSaving(true);
    try {
      const payload = {
        name,
        slug,
        description: description || null,
        base_price: Number(basePrice),
        category_id: Number(categoryId),
      };

      if (isEditing && productId) {
        await updateProductDetails(productId, payload);
        loadProduct();
      } else {
        const created = await createProduct(payload);
        navigate(`/seller/products/${created.id}`, { replace: true });
      }
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleToggleActive() {
    if (!product) return;
    setError(null);
    try {
      await setProductActive(product.id, !product.is_active);
      loadProduct();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  if (isLoading) return <LoadingSpinner label="Loading product..." />;

  return (
    <div className="page seller-product-form">
      <h1>{isEditing ? "Edit product" : "New product"}</h1>
      {error && <ErrorMessage message={error} />}

      <form className="address-form" onSubmit={handleSaveProduct}>
        <label>
          Name
          <input required value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label>
          Slug
          <input required value={slug} onChange={(e) => setSlug(e.target.value)} />
        </label>
        <label>
          Description
          <textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        <div className="form-row">
          <label>
            Base price
            <input
              required
              type="number"
              min="0.01"
              step="0.01"
              value={basePrice}
              onChange={(e) => setBasePrice(e.target.value)}
            />
          </label>
          <label>
            Category
            <select required value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
              <option value="" disabled>
                Select a category
              </option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="form-row">
          <button type="submit" className="button primary" disabled={isSaving || !categoryId}>
            {isSaving ? "Saving..." : "Save product"}
          </button>
          {isEditing && product && (
            <button type="button" className="button" onClick={handleToggleActive}>
              {product.is_active ? "Deactivate product" : "Activate product"}
            </button>
          )}
        </div>
      </form>

      {isEditing && product && (
        <VariantsManager product={product} onChanged={loadProduct} />
      )}
    </div>
  );
}

function VariantsManager({
  product,
  onChanged,
}: {
  product: ProductDetail;
  onChanged: () => void;
}) {
  return (
    <section className="section">
      <h2>Variants</h2>
      {!product.is_active && (
        <p className="hint">Reactivate this product to add or edit variants.</p>
      )}

      {product.variants.length === 0 ? (
        <p className="empty-state">No variants yet.</p>
      ) : (
        <ul className="variant-manage-list">
          {product.variants.map((variant) => (
            <VariantRow
              key={variant.id}
              productId={product.id}
              productActive={product.is_active}
              variant={variant}
              onChanged={onChanged}
            />
          ))}
        </ul>
      )}

      {product.is_active && (
        <AddVariantForm productId={product.id} onAdded={onChanged} />
      )}
    </section>
  );
}

function VariantRow({
  productId,
  productActive,
  variant,
  onChanged,
}: {
  productId: string;
  productActive: boolean;
  variant: ProductVariant;
  onChanged: () => void;
}) {
  const [price, setPrice] = useState(String(variant.price));
  const [isSavingPrice, setIsSavingPrice] = useState(false);
  const [isStockOpen, setIsStockOpen] = useState(false);
  const [quantity, setQuantity] = useState<string>("");
  const [reorderLevel, setReorderLevel] = useState<string>("");
  const [isSavingStock, setIsSavingStock] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSavePrice() {
    setError(null);
    setIsSavingPrice(true);
    try {
      await updateVariantDetails(productId, variant.id, { price: Number(price) });
      onChanged();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsSavingPrice(false);
    }
  }

  async function handleToggleActive() {
    setError(null);
    try {
      await setVariantActive(productId, variant.id, !variant.is_active);
      onChanged();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  async function openStockEditor() {
    setIsStockOpen(true);
    try {
      const inventory = await getInventory(variant.id);
      setQuantity(String(inventory.quantity));
      setReorderLevel(String(inventory.reorder_level));
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  async function handleSaveStock() {
    setError(null);
    setIsSavingStock(true);
    try {
      await updateInventory(variant.id, Number(quantity), Number(reorderLevel));
      setIsStockOpen(false);
      onChanged();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsSavingStock(false);
    }
  }

  return (
    <li className="variant-manage-row">
      <div className="variant-manage-header">
        <strong>{variant.sku}</strong>
        {Object.keys(variant.attributes).length > 0 && (
          <span className="hint"> — {Object.entries(variant.attributes).map(([k, v]) => `${k}: ${v}`).join(", ")}</span>
        )}
        <span className={variant.is_active ? "badge active" : "badge inactive"}>
          {variant.is_active ? "Active" : "Inactive"}
        </span>
      </div>

      {error && <ErrorMessage message={error} />}

      <div className="variant-manage-controls">
        <label>
          Price
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            disabled={!productActive}
          />
        </label>
        <button type="button" className="button" onClick={handleSavePrice} disabled={isSavingPrice || !productActive}>
          Save price
        </button>
        <button type="button" className="button" onClick={handleToggleActive}>
          {variant.is_active ? "Deactivate" : "Activate"}
        </button>
        <button type="button" className="button" onClick={openStockEditor}>
          Manage stock ({variant.available_quantity} available)
        </button>
      </div>

      {isStockOpen && (
        <div className="stock-editor">
          <label>
            Quantity on hand
            <input type="number" min="0" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          </label>
          <label>
            Reorder level
            <input type="number" min="0" value={reorderLevel} onChange={(e) => setReorderLevel(e.target.value)} />
          </label>
          <button type="button" className="button primary" onClick={handleSaveStock} disabled={isSavingStock}>
            {isSavingStock ? "Saving..." : "Save stock"}
          </button>
        </div>
      )}
    </li>
  );
}

function AddVariantForm({ productId, onAdded }: { productId: string; onAdded: () => void }) {
  const [sku, setSku] = useState("");
  const [price, setPrice] = useState("");
  const [attributesText, setAttributesText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await createVariant(productId, {
        sku,
        price: Number(price),
        attributes: parseAttributes(attributesText),
      });
      setSku("");
      setPrice("");
      setAttributesText("");
      onAdded();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="address-form" onSubmit={handleSubmit} style={{ marginTop: "1.25rem" }}>
      <h3>Add a variant</h3>
      {error && <ErrorMessage message={error} />}
      <label>
        SKU
        <input required value={sku} onChange={(e) => setSku(e.target.value)} />
      </label>
      <label>
        Price
        <input
          required
          type="number"
          min="0.01"
          step="0.01"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
        />
      </label>
      <label>
        Attributes (e.g. color: Red, size: M)
        <input value={attributesText} onChange={(e) => setAttributesText(e.target.value)} />
      </label>
      <button type="submit" className="button primary" disabled={isSubmitting}>
        {isSubmitting ? "Adding..." : "Add variant"}
      </button>
    </form>
  );
}
