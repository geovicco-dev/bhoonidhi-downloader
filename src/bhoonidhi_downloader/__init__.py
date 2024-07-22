import typer
from bhoonidhi_downloader.authenticate import login, save_session_info, validate_session, load_session_info
from bhoonidhi_downloader.constants import session_info
from rich.console import Console
from bhoonidhi_downloader.scene_search import search_for_scenes
from bhoonidhi_downloader.utils import get_download_url, download_scene, display_search_results, get_scenes_data_for_export, export_search_results
from geopandas import GeoDataFrame
from shapely.geometry import box
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
from typing import Optional

console = Console()
app = typer.Typer()

@app.command()
def authenticate(username: str = typer.Option(..., prompt=True, help="Bhoonidhi username"),password: str = typer.Option(..., prompt=True, hide_input=True, help="Bhoonidhi password")):
    typer.echo("Logging in...")
    
    if not username or not password:
        typer.echo("Username and password cannot be empty.", err=True)
        raise typer.Exit(code=1)
    try:
        session = login(username, password)
        session_info["jwt"] = session["JWT"]
        session_info["userId"] = session["USERID"]
        session_info["user_email"] = session["USEREMAIL"]
        session_info["username"] = session["USERNAME"]
        validate_session(session_info["jwt"])
        save_session_info(session_info)
        typer.echo("Login successful!")
    except Exception:
        typer.echo(f"Login failed! Try again.", err=True)
        raise typer.Exit(code=1)

@app.command()
def search(
    minx: float = typer.Argument(..., help="Minimum longitude"),
    maxx: float = typer.Argument(..., help="Maximum longitude"),
    miny: float = typer.Argument(..., help="Minimum latitude"),
    maxy: float = typer.Argument(..., help="Maximum latitude"),
    start_date: datetime = typer.Argument(..., formats=["%Y-%m-%d"], help="Start date (YYYY-MM-DD)"),
    end_date: datetime = typer.Argument(..., formats=["%Y-%m-%d"], help="End date (YYYY-MM-DD)"),
    satellite: str = typer.Option(None, "--sat", help="Satellite name (Ex: ResourceSat-2)"),
    sensor: str = typer.Option(None, "--sen", help="Sensor name (Ex: LISS3)"),
    csv: Optional[Path] = typer.Option(None, "--csv", help="Export results as CSV"),
    json: Optional[Path] = typer.Option(None, "--json", help="Export results as JSON"),
    markdown: Optional[Path] = typer.Option(None, "--md", help="Export results as Markdown table"),
):
  
    # Check if bounding box is valid
    if minx >= maxx or miny >= maxy:
        typer.echo("Invalid bounding box.", err=True)
        typer.Abort()
    
    # Check if start and end dates are valid
    elif start_date > end_date:
        typer.echo("Start date cannot be greater than end date.", err=True)
        typer.Abort()
    
    else:    
        # Create GeoDataFrame from bounding box
        gdf = GeoDataFrame(geometry=[box(minx, miny, maxx, maxy)], crs="EPSG:4326")

        # Load session info
        session = load_session_info()
        if not session.get("jwt"):
            typer.echo(">>>>> Please login first using authenticate command.", err=True)
            raise typer.Exit(code=1)

        # Search for scenes
        scenes = search_for_scenes(gdf, satellite, sensor, start_date, end_date, session)
            
        if len(scenes) == 0:
                print("No scenes found.")
                typer.Exit(code=1)
        else:
            session['sid'] = scenes[0]['srt']
            print(f"Search ID: {session['sid']}")
        
            # Filter scenes
            open_data_scenes = [scene for scene in scenes if scene['PRICED'] == 'OpenData_DirectDownload']
                
            if not open_data_scenes:
                typer.echo("No open data - direct download scenes found.", err=True)
                raise typer.Exit(code=1)
            else:
                typer.echo(f"Total Scenes Found: {len(open_data_scenes)}")
                
                # Sort scenes by date
                open_data_scenes.sort(key=lambda x: datetime.strptime(x.get('DOP', '01-Jan-1900'), '%d-%b-%Y'), reverse=False)
                
                # Save searched scenes to session
                for scene in open_data_scenes:
                    session["scenes"].append(scene)
                save_session_info(session)
                    
            # Display scenes in a table
            display_search_results(open_data_scenes, console)
            
            # Export search results as CSV, JSON, or Markdown table
            if open_data_scenes:
                # Prepare data for export
                export_data = get_scenes_data_for_export(open_data_scenes)
                if csv:
                    export_search_results('csv', export_data, csv)
                if json:
                    export_search_results('json', export_data, json)
                if markdown:
                    export_search_results('markdown', export_data, markdown)
    
            while True:    
                choice = typer.prompt("\nEnter the indices of the scenes you want to download - separated by comma (for multiple scenes) or 'q' to quit (example: 1,2,3) ", type=str)
                if choice.lower() == 'q':
                    raise typer.Exit()
                
                # Convert choice to list by stripping any whitespaces and split by comma
                try:
                    choice = [int(x.strip()) for x in choice.split(',')]
                except ValueError:
                    typer.echo(">>>>> Invalid input. Please enter numbers separated by commas or 'q' to quit.")
                    continue
                
                scenes_to_download = [] 
                for scene_idx in choice:
                    index = scene_idx - 1
                    if 0 <= index < len(open_data_scenes):
                        selected_scene = open_data_scenes[index]
                        scenes_to_download.append(selected_scene)
                    else:
                        typer.echo(f">>>>> Invalid index: {scene_idx}. Skipping.")

                if not scenes_to_download:
                    typer.echo(">>>>> No valid scenes selected. Please try again or press 'q' to quit.")
                    continue

                selected_scenes = [scene['ID'] for scene in scenes_to_download] if len(scenes_to_download) > 1 else scenes_to_download[0]['ID']
                typer.echo(f"\nSelected scene(s): {selected_scenes}")
                
                # Prompt user for confirmation
                if len(scenes_to_download) > 0:
                    confirm = typer.confirm(f"\nDo you want to download the above scene(s)?")
            
                if confirm:
                    # Ask user for output directory once
                    out_dir = typer.prompt("\nEnter the output directory (defaults to download folder inside current directory): ", default="./downloads", type=Path)
                    out_dir = Path(out_dir).expanduser().resolve()
                    out_dir.mkdir(parents=True, exist_ok=True)
                    
                    scene_ids = [scene['ID'] for scene in scenes_to_download]
                    download_urls = [get_download_url(scene_id, session) for scene_id in scene_ids]

                    # Download scenes
                    for url, scene_id in tqdm(zip(download_urls, scene_ids), total=len(download_urls), desc="Downloading scenes"):
                        typer.echo(download_scene(url, out_dir, scene_id))
                    typer.echo("All downloads completed.")
                    break
                else:
                    typer.Exit()
                    break
            typer.Exit()
                    
    
def main():
    app()