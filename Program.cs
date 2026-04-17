using System.Text;

if (args.Length != 3)
{
    Console.WriteLine("Usage: ConsoleApp1 <file1.tsv> <file2.tsv> <2nd name>");
    return;
}

var file1Entries = LoadEntries(args[0]);
var file2Entries = LoadEntries(args[1]);
var otherName = args[2];

var hashMismatches = new List<Mismatch>();
var sizeMismatches = new List<Mismatch>();
var missingInFile2 = new List<Mismatch>();
var missingInFile1 = new List<Mismatch>();
var matches = new List<Mismatch>();

// Check file1 against file2
foreach (var kvp in file1Entries)
{
    var path = kvp.Key;
    var entry1 = kvp.Value;

    if (file2Entries.TryGetValue(path, out var entry2))
    {
        bool hashEqual = entry1.Md5.Equals(entry2.Md5, StringComparison.OrdinalIgnoreCase);
        bool sizeEqual = entry1.Size == entry2.Size;

        if (hashEqual && sizeEqual)
            matches.Add(new Mismatch { Path = path, Entry1 = entry1, Entry2 = entry2 });
        else
        {
            if (!hashEqual)
                hashMismatches.Add(new Mismatch { Path = path, Entry1 = entry1, Entry2 = entry2 });

            if (!sizeEqual)
                sizeMismatches.Add(new Mismatch { Path = path, Entry1 = entry1, Entry2 = entry2 });
        }
    }
    else
    {
        missingInFile2.Add(new Mismatch { Path = path, Entry1 = entry1 });
    }
}

// Check file2 against file1
foreach (var kvp in file2Entries)
{
    if (!file1Entries.ContainsKey(kvp.Key))
    {
        missingInFile1.Add(new Mismatch { Path = kvp.Key, Entry2 = kvp.Value });
    }
}

string html = GenerateHtmlReport(matches, hashMismatches, sizeMismatches, missingInFile1, missingInFile2);
File.WriteAllText($"/storage/casc/report_{otherName.ToLower()}.html", html);

Console.WriteLine("Comparison complete.");

static Dictionary<string, FileEntry> LoadEntries(string filePath)
{
    var entries = new Dictionary<string, FileEntry>();

    foreach (var line in File.ReadLines(filePath))
    {
        //if (line.Contains("/wow/patch/", StringComparison.OrdinalIgnoreCase))
        //    continue;
        //if (line.Contains("/wow/config/", StringComparison.OrdinalIgnoreCase))
        //    continue;
        if (string.IsNullOrWhiteSpace(line)) continue;

        var parts = line.Split('\t');
        if (parts.Length != 3) continue;

        string path = parts[0];
        if (!long.TryParse(parts[1], out long size)) continue;

        string md5 = parts[2];

        if (md5 == "d41d8cd98f00b204e9800998ecf8427e" || md5 == "998368d7c95ea4293237f2320546e440")
            continue;

        entries[path] = new FileEntry
        {
            Path = path,
            Size = size,
            Md5 = md5
        };
    }

    return entries;
}

string GenerateHtmlReport(
    List<Mismatch> matches,
    List<Mismatch> hashMismatches,
    List<Mismatch> sizeMismatches,
    List<Mismatch> missingInFile1,
    List<Mismatch> missingInFile2)
{
    var sb = new StringBuilder();

    sb.AppendLine("<!DOCTYPE html><html><head><meta charset='UTF-8'>");
    sb.AppendLine("<title>File Comparison Report</title>");
    sb.AppendLine("<style>");
    sb.AppendLine("body { font-family: sans-serif; background: #111; color: #eee; padding: 20px; }");
    sb.AppendLine("table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }");
    sb.AppendLine("th, td { border: 1px solid #444; padding: 8px; text-align: left; }");
    sb.AppendLine("th { background-color: #222; }");
    sb.AppendLine(".match { background-color: #1a3; }");
    sb.AppendLine(".mismatch { background-color: #933; }");
    sb.AppendLine(".warning { background-color: #963; }");
    sb.AppendLine(".missing { background-color: #555; }");
    sb.AppendLine("summary { font-size: 1.2em; font-weight: bold; margin-bottom: 10px; cursor: pointer; }");
    sb.AppendLine("details { margin-bottom: 20px; border: 1px solid #444; border-radius: 5px; padding: 10px; background: #1a1a1a; }");
    sb.AppendLine("</style></head><body>");

    sb.AppendLine("<h1>File Comparison Report</h1>");

    //WriteTable(sb, "✅ Matches", matches, "match", openByDefault: false);
    WriteTable(sb, "❌ Hash Mismatches", hashMismatches, "mismatch");
    WriteTable(sb, "⚠️ Size Mismatches", sizeMismatches, "warning");
    WriteTable(sb, $"🚫 Missing in {otherName}", missingInFile1, "missing");
    WriteTable(sb, "🚫 Missing in Wago", missingInFile2, "missing");

    sb.AppendLine("</body></html>");
    return sb.ToString();
}

void WriteTable(StringBuilder sb, string title, List<Mismatch> items, string cssClass, bool openByDefault = false)
{
    sb.AppendLine(openByDefault
        ? $"<details open><summary>{title} ({items.Count})</summary>"
        : $"<details><summary>{title} ({items.Count})</summary>");

    if (items.Count == 0)
    {
        sb.AppendLine("<p>None</p>");
        sb.AppendLine("</details>");
        return;
    }

    sb.AppendLine("<table>");
    sb.AppendLine($"<tr><th>Path</th><th>{otherName} Size</th><th>Wago Size</th><th>{otherName} MD5</th><th>Wago MD5</th></tr>");

    foreach (var item in items)
    {
        sb.AppendLine($"<tr class='{cssClass}'>");
        sb.AppendLine($"<td>{item.Path}</td>");
        sb.AppendLine($"<td>{item.Entry1?.Size.ToString() ?? "-"}</td>");
        sb.AppendLine($"<td>{item.Entry2?.Size.ToString() ?? "-"}</td>");
        sb.AppendLine($"<td>{item.Entry1?.Md5 ?? "-"}</td>");
        sb.AppendLine($"<td>{item.Entry2?.Md5 ?? "-"}</td>");
        sb.AppendLine("</tr>");
    }

    sb.AppendLine("</table>");
    sb.AppendLine("</details>");
}

class FileEntry
{
    public string Path;
    public long Size;
    public string Md5;
}

class Mismatch
{
    public string Path;
    public FileEntry? Entry1;
    public FileEntry? Entry2;
}