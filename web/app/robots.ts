import { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
    return {
        rules: [
            {
                userAgent: "*",
                allow: "/",
                disallow: ["/prediction-history/", "/analyze/", "/predict?type=batch"]
            }
        ],
        sitemap: `${process.env.CLIENT_URL}/sitemap.xml`
    }
}