export async function didUserInstallSpeckGithub(
  token: string,
): Promise<boolean> {
  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/github/authenticate`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    );
    const data = await response.json();
    return data.success;
  } catch (error) {
    console.error("Error fetching GitHub auth status:", error);
    return false;
  }
}

export async function getSpeckInstalledOrgs(token: string): Promise<string[]> {
  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/github/get_installations`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    );
    const data = await response.json();
    return data.success ? data.installations : [];
  } catch (error) {
    console.error("Error fetching GitHub auth status:", error);
    return [];
  }
}

export async function refreshGithubInstallations(token: string): Promise<{
  success: boolean;
  installations: string[];
  addedCount: number;
}> {
  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/github/refresh_installations`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    );
    const data = await response.json();
    return {
      success: data.success,
      installations: data.success ? data.installations : [],
      addedCount: data.success ? data.added_count : 0,
    };
  } catch (error) {
    console.error("Error refreshing GitHub installations:", error);
    return {
      success: false,
      installations: [],
      addedCount: 0,
    };
  }
}

export async function validateGithubUser(
  token: string,
): Promise<string | null> {
  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/github/validate_user`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    );
    const data = await response.json();
    return data.success ? data.username : null;
  } catch (error) {
    console.error("Error validating GitHub user:", error);
    return null;
  }
}
