"""
DockAI Container Registry Integration.

This module provides functionality to interact with various container registries
(Docker Hub, GCR, Quay.io, ECR) to verify image existence and fetch valid tags.
This is critical for preventing the AI from hallucinating non-existent image tags.
"""

import httpx
import logging
from typing import List

from .rate_limiter import handle_registry_rate_limit

# Initialize logger for the 'dockai' namespace
logger = logging.getLogger("dockai")


import re
from functools import lru_cache
from typing import List, Optional, Tuple


def _strip_tag(image_name: str) -> Tuple[str, Optional[str]]:
    """Split image into (repo, tag) without breaking registry hosts.

    We only treat a ':' as a tag separator if it appears *after* the last '/'.
    This prevents mis-parsing registries that include a port (e.g. gcr:5000/foo).
    """
    last_slash = image_name.rfind("/")
    last_colon = image_name.rfind(":")
    if last_colon > last_slash:
        return image_name[:last_colon], image_name[last_colon + 1 :]
    return image_name, None

@lru_cache(maxsize=128)
@handle_registry_rate_limit
def get_docker_tags(image_name: str, limit: int = 5, target_version: Optional[str] = None) -> List[str]:
    """
    Fetches valid tags for a given Docker image from supported registries.
    
    This function queries the registry API to get a list of available tags for
    the specified image. It prioritizes tags that match the target_version,
    then 'alpine' and 'slim' variants. Results are cached in memory.
    
    Supported Registries:
    - Docker Hub (default)
    - Google Container Registry (gcr.io)
    - Quay.io
    - GitHub Container Registry (ghcr.io)
    - AWS ECR (limited support, skips verification)

    Args:
        image_name (str): The name of the image (e.g., 'node', 'node:20-alpine', 'gcr.io/my-project/my-image').
        limit (int, optional): The maximum number of fallback tags to return. Defaults to 5.
        target_version (str, optional): The specific version to filter for (e.g., '3.11', '20').
            If provided, only tags matching this version will be returned.

    Returns:
        List[str]: A list of verified, full image tags. Empty list if verification fails
                   (the generator will proceed with unverified tags).
    """
    # Handle empty or invalid input
    if not image_name or not image_name.strip():
        logger.debug("Empty image name provided to get_docker_tags")
        return []
    
    image_name = image_name.strip()
    
    # Strip any existing tag from the image name (e.g., "python:3.11-slim" -> "python")
    # without breaking registry hosts that include ports (gcr:5000/foo:bar).
    base_image, extracted_tag = _strip_tag(image_name)
    
    # If image_name had a tag, try to extract version from it as fallback
    if target_version is None and extracted_tag:
        version_match = re.match(r"^v?(\d+(?:\.\d+)*)", extracted_tag)
        if version_match:
            target_version = version_match.group(1)
            logger.debug(f"Extracted target version from image tag: {target_version}")
    
    logger.debug(f"Looking up tags for base image: {base_image} (target_version: {target_version})")
    
    tags = []
    
    try:
        # Dispatch to appropriate registry handler based on base_image (without tag)
        if ".dkr.ecr." in base_image and ".amazonaws.com" in base_image:
            logger.info(f"ECR image detected: {base_image}. Skipping tag verification (requires AWS credentials).")
            return []
            
        elif "gcr.io" in base_image:
            logger.debug(f"Fetching tags from GCR for: {base_image}")
            tags = _fetch_gcr_tags(base_image)
            
        elif "quay.io" in base_image:
            logger.debug(f"Fetching tags from Quay for: {base_image}")
            tags = _fetch_quay_tags(base_image)
            
        elif "ghcr.io" in base_image:
            logger.debug(f"Fetching tags from GHCR for: {base_image}")
            tags = _fetch_ghcr_tags(base_image)
            
        else:
            logger.debug(f"Fetching tags from Docker Hub for: {base_image}")
            tags = _fetch_docker_hub_tags(base_image, target_version)

        if not tags:
            logger.debug(f"No tags found for {base_image} - will use AI-suggested tags without verification")
            return []

        # Filter and sort tags, prioritizing target_version if provided
        processed = _process_tags(base_image, tags, limit, target_version)
        if processed:
            logger.debug(f"Found {len(processed)} verified tags for {base_image}")
        return processed
        
    except Exception as e:
        logger.warning(f"Failed to fetch tags for {base_image}: {e}")
        return []


def _fetch_docker_hub_tags(image_name: str, target_version: Optional[str] = None) -> List[str]:
    """
    Fetch tags from Docker Hub using Hub API (with filter) and Registry v2 API (fallback).
    
    Docker Hub has two APIs:
    1. Hub API (hub.docker.com) - Supports name= filter, efficient for targeted searches
    2. Registry API (registry-1.docker.io) - Returns ALL tags, comprehensive fallback
    
    Strategy:
    - If target_version is provided (from AI suggestion), use Hub API with name= filter
      This is efficient and returns only relevant tags (~100 filtered results)
    - If Hub API fails or returns no results, fall back to Registry v2 API which
      returns ALL tags (comprehensive but returns thousands)
    
    This approach minimizes token waste by leveraging the AI's version suggestion
    to filter at the API level.
    
    Args:
        image_name: The image name (e.g., 'node', 'python')
        target_version: Optional version to filter for (e.g., '18', '3.11')
    """
    # Handle official images (e.g., 'node' -> 'library/node')
    hub_image_name = image_name
    if "/" not in hub_image_name:
        hub_image_name = f"library/{hub_image_name}"
    elif hub_image_name.startswith("docker.io/"):
        hub_image_name = hub_image_name.replace("docker.io/", "")
    
    # Try Hub API first with name= filter (efficient when target_version is known)
    tags = _fetch_docker_hub_api(hub_image_name, target_version)
    if tags:
        return tags
    
    # Fallback to Registry v2 API (returns ALL tags - comprehensive but larger response)
    logger.debug(f"Hub API returned no results for {hub_image_name}, trying Registry v2 API...")
    return _fetch_docker_registry_v2_tags(hub_image_name)


def _fetch_docker_hub_api(hub_image_name: str, target_version: Optional[str] = None) -> List[str]:
    """
    Fetch tags using Docker Hub's proprietary API.
    
    The Docker Hub API supports a 'name' query parameter to filter tags.
    This is critical for finding older LTS versions like Node 18 that may
    not appear in the first 100 most recent tags.
    
    Strategy:
    - If target_version is provided, use name= filter to get matching tags
    - If filter returns nothing (AI suggested non-existent version), return empty
      so the caller can fall back to Registry v2 for ALL tags
    - The AI can then pick the correct version from the complete tag list
    
    Args:
        hub_image_name: The full image name (e.g., 'library/node')
        target_version: Optional version to filter for (e.g., '18', '3.11')
    """
    url = f"https://hub.docker.com/v2/repositories/{hub_image_name}/tags"
    
    # Build query params - use 'name' filter if target_version is specified
    params = {"page_size": 100}
    if target_version:
        # Filter tags containing the target version (e.g., '18' matches '18-alpine', '18.20.8')
        params["name"] = target_version
        logger.debug(f"Docker Hub: Filtering tags with name={target_version}")
    
    try:
        response = httpx.get(url, params=params, timeout=10.0)
        
        if response.status_code == 200:
            results = response.json().get("results", [])
            tags = [r["name"] for r in results]
            
            # If we filtered by version and got results, we're done
            if target_version and tags:
                logger.debug(f"Docker Hub: Found {len(tags)} tags matching '{target_version}'")
                return tags
            
            # If filtered search returned nothing, return empty to trigger Registry v2 fallback
            # This happens when AI suggests a non-existent version
            if target_version and not tags:
                logger.info(f"Docker Hub: No tags found matching '{target_version}' - will fetch ALL tags")
                return []  # Caller will fall back to Registry v2 for complete tag list
            
            return tags
        elif response.status_code == 404:
            logger.debug(f"Docker Hub: Image '{hub_image_name}' not found (404)")
        elif response.status_code == 429:
            logger.warning(f"Docker Hub: Rate limited (429)")
        else:
            logger.debug(f"Docker Hub API returned {response.status_code} for {hub_image_name}")
    except httpx.TimeoutException:
        logger.debug(f"Docker Hub API timeout for {hub_image_name}")
    except Exception as e:
        logger.debug(f"Docker Hub API error for {hub_image_name}: {e}")
    
    return []


def _fetch_docker_registry_v2_tags(image_name: str) -> List[str]:
    """
    Fetch tags using Docker Registry v2 API with anonymous token.
    
    This is the OCI-standard way to access Docker Hub programmatically.
    Requires getting an anonymous token first.
    """
    try:
        # Step 1: Get anonymous auth token
        token_url = f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{image_name}:pull"
        token_response = httpx.get(token_url, timeout=10.0)
        
        if token_response.status_code != 200:
            logger.debug(f"Failed to get Docker token: {token_response.status_code}")
            return []
        
        token = token_response.json().get("token")
        if not token:
            logger.debug("No token in Docker auth response")
            return []
        
        # Step 2: Fetch tags with the token
        tags_url = f"https://registry-1.docker.io/v2/{image_name}/tags/list"
        headers = {"Authorization": f"Bearer {token}"}
        tags_response = httpx.get(tags_url, headers=headers, timeout=10.0)
        
        if tags_response.status_code == 200:
            return tags_response.json().get("tags", [])
        elif tags_response.status_code == 404:
            logger.debug(f"Registry v2: Image '{image_name}' not found (404)")
        else:
            logger.debug(f"Registry v2 API returned {tags_response.status_code} for {image_name}")
            
    except httpx.TimeoutException:
        logger.debug(f"Registry v2 API timeout for {image_name}")
    except Exception as e:
        logger.debug(f"Registry v2 API error for {image_name}: {e}")
    
    return []


def _fetch_gcr_tags(image_name: str) -> List[str]:
    """Fetch tags from Google Container Registry."""
    # Format: gcr.io/project/image
    repo_path = image_name.split("/", 1)[1] if "/" in image_name else image_name
    domain = image_name.split("/")[0]
    url = f"https://{domain}/v2/{repo_path}/tags/list"
    
    try:
        response = httpx.get(url, timeout=10.0)
        if response.status_code == 200:
            return response.json().get("tags", [])
        elif response.status_code == 404:
            logger.debug(f"GCR: Image '{image_name}' not found (404)")
        elif response.status_code == 401:
            logger.debug(f"GCR: Authentication required for '{image_name}' (401)")
        else:
            logger.debug(f"GCR API returned {response.status_code} for {image_name}")
    except httpx.TimeoutException:
        logger.debug(f"GCR API timeout for {image_name}")
    except Exception as e:
        logger.debug(f"GCR API error for {image_name}: {e}")
    
    return []


def _fetch_quay_tags(image_name: str) -> List[str]:
    """
    Fetch tags from Quay.io.
    
    Quay.io uses pagination (50 tags per page). We fetch all pages to get
    the complete tag list, similar to how we handle Docker Hub.
    """
    # Format: quay.io/namespace/image
    repo_path = image_name.split("/", 1)[1] if "/" in image_name else image_name
    base_url = f"https://quay.io/api/v1/repository/{repo_path}/tag/"
    
    all_tags = []
    page = 1
    max_pages = 20  # Safety limit to prevent infinite loops
    
    try:
        while page <= max_pages:
            params = {"page": page}
            response = httpx.get(base_url, params=params, timeout=10.0, follow_redirects=True)
            
            if response.status_code == 200:
                data = response.json()
                tags = data.get("tags", [])
                all_tags.extend([t["name"] for t in tags])
                
                # Check if there are more pages
                if not data.get("has_additional", False):
                    break
                page += 1
            elif response.status_code == 404:
                logger.debug(f"Quay: Image '{image_name}' not found (404)")
                break
            elif response.status_code == 401:
                logger.debug(f"Quay: Authentication required for '{image_name}' (401)")
                break
            else:
                logger.debug(f"Quay API returned {response.status_code} for {image_name}")
                break
                
        if all_tags:
            logger.debug(f"Quay: Fetched {len(all_tags)} tags across {page} page(s)")
        return all_tags
        
    except httpx.TimeoutException:
        logger.debug(f"Quay API timeout for {image_name}")
    except Exception as e:
        logger.debug(f"Quay API error for {image_name}: {e}")
    
    return all_tags if all_tags else []


def _fetch_ghcr_tags(image_name: str) -> List[str]:
    """
    Fetch tags from GitHub Container Registry.
    
    GHCR requires authentication even for public images in most cases.
    We try anonymous access first, then attempt to get an anonymous token.
    """
    repo_path = image_name.split("/", 1)[1] if "/" in image_name else image_name
    
    # Try with anonymous token first (GHCR's OCI-compliant approach)
    try:
        # Get anonymous token
        token_url = f"https://ghcr.io/token?scope=repository:{repo_path}:pull"
        token_response = httpx.get(token_url, timeout=10.0)
        
        if token_response.status_code == 200:
            token = token_response.json().get("token")
            if token:
                # Fetch tags with token
                tags_url = f"https://ghcr.io/v2/{repo_path}/tags/list"
                headers = {"Authorization": f"Bearer {token}"}
                tags_response = httpx.get(tags_url, headers=headers, timeout=10.0)
                
                if tags_response.status_code == 200:
                    return tags_response.json().get("tags", [])
                elif tags_response.status_code == 404:
                    logger.debug(f"GHCR: Image '{image_name}' not found (404)")
                elif tags_response.status_code == 401:
                    logger.debug(f"GHCR: Authentication required for '{image_name}' - package may be private")
                else:
                    logger.debug(f"GHCR API returned {tags_response.status_code} for {image_name}")
        else:
            logger.debug(f"GHCR token request returned {token_response.status_code}")
            
    except httpx.TimeoutException:
        logger.debug(f"GHCR API timeout for {image_name}")
    except Exception as e:
        logger.debug(f"GHCR API error for {image_name}: {e}")
    
    return []


def _process_tags(image_name: str, tags: List[str], limit: int, target_version: Optional[str] = None) -> List[str]:
    """
    Filter, sort, and format the fetched tags.
    
    Args:
        image_name: The base image name (for prefix building)
        tags: Raw list of tags from the registry
        limit: Maximum number of tags to return
        target_version: If provided, prioritize tags matching this version (e.g., '3.11', '20')
    """
    # Filter out unstable tags
    version_tags = [t for t in tags if t not in ["latest", "stable", "edge", "nightly", "canary"]]
    
    if not version_tags:
        return []

    prefix = _get_image_prefix(image_name)
    
    # If target_version is specified, use it instead of detecting latest
    if target_version:
        logger.info(f"Using target version for {image_name}: {target_version}")
        
        # Get all tags that match the target version
        target_specific_tags = [
            t for t in tags 
            if t.startswith(target_version) or 
               t.startswith(f"v{target_version}") or
               t == target_version
        ]
        
        if target_specific_tags:
            # Sort: Alpine first, then Slim, then others
            def preference_sort(tag):
                score = 0
                if "alpine" in tag: score -= 2
                elif "slim" in tag: score -= 1
                if "window" in tag: score += 10  # Penalize windows images
                return score
                
            final_tags = sorted(target_specific_tags, key=preference_sort)
            return [f"{prefix}{t}" for t in final_tags]
        else:
            logger.warning(f"No tags found matching target version '{target_version}' for {image_name}")
            # Fall through to detect latest
    
    # Sort tags semantically to find the latest versions
    sorted_versions = _sort_tags_semantically(version_tags)
    
    if not sorted_versions:
        # Fallback to original list if sorting fails
        sorted_versions = version_tags

    # Get the latest version (first in the sorted list)
    latest_tag = sorted_versions[0]
    
    # Extract the version number part (e.g., "3.11" from "3.11-slim")
    match = re.match(r"^v?(\d+(?:\.\d+)*)", latest_tag)
    latest_version_prefix = match.group(1) if match else None

    if latest_version_prefix:
        logger.info(f"Detected latest version for {image_name}: {latest_version_prefix}")
        
        # Get all tags that start with this version prefix
        version_specific_tags = [t for t in tags if t.startswith(latest_version_prefix) or (t.startswith("v") and t[1:].startswith(latest_version_prefix))]
        
        # Sort: Alpine first, then Slim, then others
        def preference_sort(tag):
            score = 0
            if "alpine" in tag: score -= 2
            elif "slim" in tag: score -= 1
            if "window" in tag: score += 10  # Penalize windows images
            return score
            
        final_tags = sorted(version_specific_tags, key=preference_sort)
        return [f"{prefix}{t}" for t in final_tags]

    # Fallback Mix Strategy
    alpine_tags = [t for t in tags if "alpine" in t]
    slim_tags = [t for t in tags if "slim" in t]
    standard_tags = [t for t in tags if "alpine" not in t and "slim" not in t and "window" not in t]
    
    selected_tags = []
    selected_tags.extend(alpine_tags[:2])
    selected_tags.extend(slim_tags[:2])
    selected_tags.extend(standard_tags[:1])
    
    if len(selected_tags) >= 3:
        unique_tags = sorted(list(set(selected_tags)), reverse=True)
        return [f"{prefix}{t}" for t in unique_tags]
        
    return [f"{prefix}{t}" for t in tags[:limit]]


def _sort_tags_semantically(tags: List[str]) -> List[str]:
    """
    Sorts tags based on semantic versioning (highest first).
    Handles tags like '1.2.3', 'v1.2.3', '1.2.3-alpine'.
    """
    def version_key(tag):
        # Extract the version number part
        match = re.match(r"^v?(\d+(?:\.\d+)*)", tag)
        if not match:
            return (0, 0, 0) # Low priority for non-version tags
        
        version_str = match.group(1)
        try:
            # Convert "1.2.3" to (1, 2, 3)
            return tuple(map(int, version_str.split('.')))
        except ValueError:
            return (0, 0, 0)

    # Sort descending (highest version first)
    return sorted(tags, key=version_key, reverse=True)


def _get_image_prefix(image_name: str) -> str:
    """
    Determines the correct prefix for an image based on its registry.
    
    This ensures consistent tag formatting across all registries (e.g., keeping
    the full registry path for GCR/Quay, but simplifying for Docker Hub).

    Args:
        image_name (str): The raw image name.

    Returns:
        str: The formatted prefix (e.g., 'node:', 'gcr.io/my-project/my-image:').
    """
    # For registries with explicit domains, keep the full image name
    if any(registry in image_name for registry in ["gcr.io", "quay.io", "ghcr.io", ".dkr.ecr.", "azurecr.io"]):
        return f"{image_name}:"
    
    # For Docker Hub, normalize the name
    # Remove 'library/' prefix for official images to keep it clean and standard
    clean_name = image_name.replace("docker.io/", "").replace("library/", "")
    return f"{clean_name}:"
