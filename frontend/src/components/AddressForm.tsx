import { useState } from "react";
import type { FormEvent } from "react";
import type { AddressInput } from "../types";

export function AddressForm({
  onSubmit,
  onCancel,
  isSubmitting,
}: {
  onSubmit: (payload: AddressInput) => void;
  onCancel?: () => void;
  isSubmitting: boolean;
}) {
  const [addressLine1, setAddressLine1] = useState("");
  const [addressLine2, setAddressLine2] = useState("");
  const [city, setCity] = useState("");
  const [region, setRegion] = useState("");
  const [postalCode, setPostalCode] = useState("");
  const [countryCode, setCountryCode] = useState("US");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit({
      address_line1: addressLine1,
      address_line2: addressLine2 || null,
      city,
      region: region || null,
      postal_code: postalCode,
      country_code: countryCode,
    });
  }

  return (
    <form className="address-form" onSubmit={handleSubmit}>
      <label>
        Address line 1
        <input required value={addressLine1} onChange={(e) => setAddressLine1(e.target.value)} />
      </label>
      <label>
        Address line 2 (optional)
        <input value={addressLine2} onChange={(e) => setAddressLine2(e.target.value)} />
      </label>
      <div className="form-row">
        <label>
          City
          <input required value={city} onChange={(e) => setCity(e.target.value)} />
        </label>
        <label>
          Region / State
          <input value={region} onChange={(e) => setRegion(e.target.value)} />
        </label>
      </div>
      <div className="form-row">
        <label>
          Postal code
          <input required value={postalCode} onChange={(e) => setPostalCode(e.target.value)} />
        </label>
        <label>
          Country code
          <input
            required
            maxLength={2}
            minLength={2}
            value={countryCode}
            onChange={(e) => setCountryCode(e.target.value.toUpperCase())}
          />
        </label>
      </div>
      <div className="form-row">
        <button type="submit" className="button primary" disabled={isSubmitting}>
          {isSubmitting ? "Saving..." : "Save address"}
        </button>
        {onCancel && (
          <button type="button" className="button" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
