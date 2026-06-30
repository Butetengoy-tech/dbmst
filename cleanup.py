import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Missing SUPABASE_URL or SUPABASE_KEY in environment/dotenv")
    exit(1)

supabase: Client = create_client(url, key)

print("Starting data cleanup...")

try:
    # Delete dummy swimmers
    res_swimmers = supabase.table('swimmers').delete().eq('birthday', '2000-01-01').eq('gender', 'Unknown').execute()
    print(f"Deleted placeholder swimmers. Affected rows: {len(res_swimmers.data)}")
    
    # Delete typo swimmer
    res_typo = supabase.table('swimmers').delete().ilike('full_name', '%Xhierywn%').execute()
    print(f"Deleted typo swimmers. Affected rows: {len(res_typo.data)}")
    
    # Delete competitions (cascades to events and race results)
    # Be careful not to delete any genuine competitions, but the ones from the screenshots were "2023 DAVRAA MEET"
    res_comp1 = supabase.table('competitions').delete().eq('name', '2023 DAVRAA MEET').execute()
    print(f"Deleted '2023 DAVRAA MEET'. Affected rows: {len(res_comp1.data)}")
    
    res_comp2 = supabase.table('competitions').delete().eq('name', '2024 DAVRAA MEET').execute()
    print(f"Deleted '2024 DAVRAA MEET'. Affected rows: {len(res_comp2.data)}")
    
    print("Cleanup completed successfully.")
except Exception as e:
    print("Error:", e)
