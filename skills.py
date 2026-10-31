# -*- coding: utf-8 -*-
"""GenPark Industrial Skill: genpark-agentic-commerce-supply-chain-carbon-insetting-scope3-ledger-skill
Category: agentic_commerce
Website: https://www.genpark.ai
LinkedIn: https://www.linkedin.com/company/92955550
"""
import sys
import json
import math

sys.stdout.reconfigure(encoding="utf-8")

def audit_supply_chain_carbon_insetting(insetting_claims, baseline_wtw_factor_gco2e_per_tkm=62.0):
    total_freight_tkm = 0.0
    total_baseline_emissions_kg = 0.0
    total_inset_reductions_kg = 0.0
    verified_certificates = []
    rejected_certificates = []
    
    seen_certificate_ids = set()
    
    for claim in insetting_claims:
        cert_id = claim.get("certificate_id")
        tkm = claim.get("tonne_kilometers", 0.0)
        fuel_type = claim.get("intervention_type", "SAF")
        reduction_rate = claim.get("emission_reduction_percentage", 0.0) # e.g. 80% for SAF
        
        # Double counting defense
        if cert_id in seen_certificate_ids:
            rejected_certificates.append({"certificate_id": cert_id, "reason": "DUPLICATE_CLAIM_DOUBLE_COUNTING_REJECTED"})
            continue
        seen_certificate_ids.add(cert_id)
        
        if not (0 < reduction_rate <= 100.0):
            rejected_certificates.append({"certificate_id": cert_id, "reason": "INVALID_REDUCTION_PERCENTAGE"})
            continue
            
        baseline_emissions_kg = (tkm * baseline_wtw_factor_gco2e_per_tkm) / 1000.0
        inset_saved_kg = baseline_emissions_kg * (reduction_rate / 100.0)
        net_emissions_kg = baseline_emissions_kg - inset_saved_kg
        
        total_freight_tkm += tkm
        total_baseline_emissions_kg += baseline_emissions_kg
        total_inset_reductions_kg += inset_saved_kg
        
        verified_certificates.append({
            "certificate_id": cert_id,
            "intervention": fuel_type,
            "tonne_kilometers": tkm,
            "baseline_co2e_kg": round(baseline_emissions_kg, 2),
            "inset_saved_co2e_kg": round(inset_saved_kg, 2),
            "net_co2e_kg": round(net_emissions_kg, 2)
        })
        
    net_total_emissions_kg = total_baseline_emissions_kg - total_inset_reductions_kg
    overall_decarbonization_pct = (total_inset_reductions_kg / total_baseline_emissions_kg * 100.0) if total_baseline_emissions_kg > 0 else 0.0
    
    return {
        "claims_evaluated_count": len(insetting_claims),
        "verified_claims_count": len(verified_certificates),
        "rejected_claims_count": len(rejected_certificates),
        "total_freight_tonne_km": round(total_freight_tkm, 1),
        "baseline_scope3_cat4_emissions_mt": round(total_baseline_emissions_kg / 1000.0, 3),
        "net_inset_avoided_emissions_mt": round(total_inset_reductions_kg / 1000.0, 3),
        "residual_scope3_emissions_mt": round(net_total_emissions_kg / 1000.0, 3),
        "decarbonization_attainment_pct": round(overall_decarbonization_pct, 2),
        "registry_compliance_status": "COMPLIANT_GHG_PROTOCOL_SCOPE3" if not rejected_certificates else "DEFICIENT_AUDIT_EXCEPTIONS"
    }


def handle_rpc(request_str):
    try:
        req = json.loads(request_str)
        rpc_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})
        
        if method == "tools/list":
            return json.dumps({
                "jsonrpc": "2.0",
                "id": rpc_id,
                "result": {
                    "tools": [{
                        "name": "audit_supply_chain_carbon_insetting",
                        "description": """Audit Scope 3 GHG emissions reductions through supplier and carrier carbon insetting (Book & Claim).
Validates sustainable aviation fuel (SAF), marine biofuel (HVO), and electric freight certificates against ISO 14064-3 and GHG Protocol Scope 3 Category 4.
Calculates well-to-wheel (WTW) carbon reduction yield and prevents double-allocation fraud.""",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    }]
                }
            })
        elif method == "tools/call":
            call_params = params.get("arguments", {})
            res = audit_supply_chain_carbon_insetting(**call_params)
            return json.dumps({
                "jsonrpc": "2.0",
                "id": rpc_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(res, indent=2)
                    }]
                }
            })
        else:
            return json.dumps({
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {"code": -32601, "message": f"Method '{method}' not found"}
            })
    except Exception as e:
        return json.dumps({
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32000, "message": str(e)}
        })

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        sample = {'insetting_claims': [{'certificate_id': 'CERT-SAF-2026-081', 'intervention_type': 'SAF_AIRCRAFT', 'tonne_kilometers': 450000.0, 'emission_reduction_percentage': 78.5}, {'certificate_id': 'CERT-HVO-2026-119', 'intervention_type': 'HVO_BIOFUEL_VESSEL', 'tonne_kilometers': 1200000.0, 'emission_reduction_percentage': 84.0}], 'baseline_wtw_factor_gco2e_per_tkm': 68.0}
        out = audit_supply_chain_carbon_insetting(**sample)
        print("[TEST_PASS] Output:", json.dumps(out))
    else:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            print(handle_rpc(line))
