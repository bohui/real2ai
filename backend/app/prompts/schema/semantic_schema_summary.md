# Diagram-Specific Semantic Schema System

## Overview

This document describes the comprehensive diagram-specific semantic schema system that provides specialized analysis capabilities for each type of diagram in the Real2AI property assessment platform.

## Architecture

### Base Class
- **`DiagramSemanticsBase`** - Abstract base class providing common functionality for all diagram types
  - Common metadata fields (title, scale, orientation, legend)
  - Universal analysis fields (textual information, spatial relationships, risk indicators)
  - Overall assessment fields (summary, impact, findings, concerns)
  - Analysis metadata (confidence, notes, follow-ups)
  - Abstract method `get_primary_focus()` for type-specific focus identification

### Specialized Semantic Classes

Each `DiagramType` has its own specialized semantic class with type-specific fields and elements:

#### **Site Plans & Boundaries**
1. **`SitePlanSemantics`** - Site layout and boundaries
   - Focus: `site_layout_and_boundaries`
   - Specific fields: `lot_dimensions`, `building_setbacks`, `access_points`, `parking_areas`
   - Elements: boundaries, buildings, infrastructure

2. **`SurveyDiagramSemantics`** - Precise boundaries and measurements
   - Focus: `precise_boundaries_and_measurements`
   - Specific fields: `survey_marks`, `measurements`, `elevation_data`, `coordinate_system`
   - Elements: boundaries

3. **`TitlePlanSemantics`** - Legal boundaries and ownership
   - Focus: `legal_boundaries_and_ownership`
   - Specific fields: `lot_numbers`, `plan_numbers`, `easements`, `owners_details`
   - Elements: boundaries

#### **Infrastructure & Utilities**
4. **`SewerServiceSemantics`** - Sewer infrastructure
   - Focus: `sewer_infrastructure`
   - Specific fields: `pipe_network`, `connection_points`, `maintenance_access`, `easement_areas`
   - Elements: infrastructure

5. **`DrainagePlanSemantics`** - Stormwater management
   - Focus: `stormwater_management`
   - Specific fields: `drainage_network`, `catchment_areas`, `outfall_points`, `retention_systems`, `pipe_capacities`
   - Elements: infrastructure

6. **`UtilityPlanSemantics`** - Utility infrastructure
   - Focus: `utility_infrastructure`
   - Specific fields: `utility_types`, `service_connections`, `easement_corridors`, `meter_locations`, `capacity_information`
   - Elements: infrastructure

#### **Environmental & Risk Assessment**
7. **`FloodMapSemantics`** - Flood risk assessment
   - Focus: `flood_risk_assessment`
   - Specific fields: `flood_zones`, `water_levels`, `escape_routes`, `flood_mitigation`
   - Elements: environmental

8. **`BushfireMapSemantics`** - Bushfire risk assessment
   - Focus: `bushfire_risk_assessment`
   - Specific fields: `bushfire_zones`, `vegetation_types`, `defensible_space`, `evacuation_routes`, `construction_requirements`
   - Elements: environmental

9. **`EnvironmentalOverlaySemantics`** - Environmental protection
   - Focus: `environmental_protection_and_restrictions`
   - Specific fields: `overlay_zones`, `protected_areas`, `development_restrictions`, `vegetation_controls`
   - Elements: environmental

10. **`ContourMapSemantics`** - Topography and elevation
    - Focus: `topography_and_elevation`
    - Specific fields: `elevation_ranges`, `contour_intervals`, `slope_analysis`, `drainage_patterns`, `cut_fill_requirements`
    - Elements: environmental

#### **Planning & Development**
11. **`ZoningMapSemantics`** - Zoning and development controls
    - Focus: `zoning_and_development_controls`
    - Specific fields: `zoning_classifications`, `development_controls`, `height_restrictions`, `land_use_permissions`
    - Elements: environmental

12. **`BuildingEnvelopePlanSemantics`** - Development constraints
    - Focus: `development_constraints`
    - Specific fields: `setback_requirements`, `height_limits`, `floor_area_ratio`, `coverage_limits`, `buildable_area`
    - Elements: buildings, boundaries

13. **`DevelopmentPlanSemantics`** - Development requirements
    - Focus: `development_requirements`
    - Specific fields: `development_stages`, `density_requirements`, `open_space_provision`, `infrastructure_contributions`, `affordable_housing`
    - Elements: buildings, boundaries, infrastructure

14. **`SubdivisionPlanSemantics`** - Subdivision layout
    - Focus: `subdivision_layout`
    - Specific fields: `lot_layout`, `road_dedications`, `easement_dedications`, `infrastructure_works`, `approval_conditions`
    - Elements: boundaries, infrastructure

15. **`HeritageOverlaySemantics`** - Heritage protection
    - Focus: `heritage_protection`
    - Specific fields: `heritage_significance`, `protection_requirements`, `development_controls`, `conservation_areas`, `permit_requirements`
    - Elements: environmental, buildings

#### **Strata & Body Corporate**
16. **`StrataPlanSemantics`** - Strata ownership structure
    - Focus: `strata_ownership_structure`
    - Specific fields: `lot_entitlements`, `common_areas`, `exclusive_use_areas`, `strata_restrictions`, `management_areas`
    - Elements: boundaries, buildings

17. **`BodyCorporatePlanSemantics`** - Body corporate management
    - Focus: `body_corporate_management`
    - Specific fields: `management_areas`, `maintenance_responsibilities`, `common_facilities`, `levies_structure`, `restrictions`
    - Elements: boundaries, buildings

#### **Landscape & Parking**
18. **`LandscapePlanSemantics`** - Landscape requirements
    - Focus: `landscape_requirements`
    - Specific fields: `vegetation_zones`, `tree_preservation`, `planting_requirements`, `irrigation_systems`, `hardscape_elements`
    - Elements: environmental

19. **`ParkingPlanSemantics`** - Parking and access
    - Focus: `parking_and_access`
    - Specific fields: `parking_spaces`, `access_arrangements`, `disabled_access`, `visitor_parking`, `loading_areas`
    - Elements: infrastructure

#### **Marketing & Visual Analysis**
20. **`OffThePlanMarketingSemantics`** - Marketing information
    - Focus: `marketing_information`
    - Specific fields: `unit_types`, `amenities`, `completion_timeline`, `pricing_information`, `marketing_features`
    - Elements: buildings

21. **`AerialViewSemantics`** - Contextual analysis
    - Focus: `contextual_analysis`
    - Specific fields: `site_context`, `access_visibility`, `neighboring_developments`, `natural_features`, `urban_fabric`
    - Elements: buildings, environmental, infrastructure

22. **`CrossSectionSemantics`** - Vertical analysis
    - Focus: `vertical_analysis`
    - Specific fields: `elevation_profile`, `subsurface_conditions`, `structural_elements`, `vertical_relationships`, `construction_challenges`
    - Elements: buildings, environmental

23. **`ElevationViewSemantics`** - Architectural appearance
    - Focus: `architectural_appearance`
    - Specific fields: `facade_treatments`, `height_relationships`, `architectural_features`, `material_specifications`, `visual_impact`
    - Elements: buildings

## Mapping System

### Automatic Type Resolution
The system automatically maps each `DiagramType` to its corresponding specialized semantic class:

```python
DIAGRAM_SEMANTICS_MAPPING = {
    DiagramType.SITE_PLAN: SitePlanSemantics,
    DiagramType.SEWER_SERVICE_DIAGRAM: SewerServiceSemantics,
    DiagramType.FLOOD_MAP: FloodMapSemantics,
    # ... all 23 types mapped to specialized classes
}
```

### Factory Functions
- **`get_semantic_schema_class(diagram_type)`** - Returns the appropriate schema class
- **`create_semantic_instance(diagram_type, **kwargs)`** - Creates instances of the correct type

### Type Safety
- **`SemanticSchema`** - Union type including all specialized semantic classes
- Full IDE support and type checking for all diagram-specific fields

## Usage Examples

### Basic Usage
```python
# Get the right schema for a diagram type
schema_class = get_semantic_schema_class(DiagramType.FLOOD_MAP)
# Returns FloodMapSemantics

# Create a specialized instance
flood_analysis = create_semantic_instance(
    DiagramType.FLOOD_MAP,
    semantic_summary="Property in low flood risk zone",
    property_impact_summary="Minimal flood impact on development",
    analysis_confidence=ConfidenceLevel.HIGH,
    flood_zones=["Zone X - minimal risk"],
    water_levels=["100-year flood level 2m below property"]
)
```

### Specialized Field Access
```python
# Site plan specific fields
site_plan = SitePlanSemantics(...)
print(site_plan.building_setbacks)  # ["6m front", "1.5m side"]
print(site_plan.lot_dimensions)     # "25m x 40m"

# Sewer service specific fields  
sewer = SewerServiceSemantics(...)
print(sewer.pipe_network)          # ["225mm main line"]
print(sewer.easement_areas)        # ["3m easement corridor"]
```

## Benefits

1. **Precision**: Each diagram type captures only relevant semantic information
2. **Efficiency**: No unnecessary fields or processing for irrelevant data
3. **Extensibility**: Easy to add new diagram types or modify existing ones
4. **Type Safety**: Strong typing prevents errors and improves IDE support
5. **Focused Analysis**: AI can provide more targeted and relevant analysis
6. **Maintainability**: Clear separation of concerns and organized code structure
7. **Backward Compatibility**: Unmapped types fall back to base class

## Coverage

✅ **100% Coverage**: All 24 `DiagramType` values have specialized semantic classes
✅ **Complete Mapping**: Every diagram type is mapped to its semantic class
✅ **Type Safety**: Full type coverage with Union types and factory functions
✅ **Documentation**: Each class documents its specific focus and capabilities

This system provides the foundation for highly specialized and accurate diagram analysis tailored to each specific document type in the property assessment workflow.
