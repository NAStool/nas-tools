import { html, nothing } from "../../utility/lit-core.min.js";
import { CustomElement, Golbal } from "../../utility/utility.js";

export class AccordionSeasons extends CustomElement {

  static properties = {
    tmdbid:  { },
    title: { },
    year: { },
    seasons_data: { type: Array },
  };

  constructor() {
    super();
    this.tmdbid = "";
    this.seasons_data = [];
  }

  _get_episodes_list(seasons) {
    // 获取季集信息
    //console.log(seasons, "get_season_episodes", "season" + seasons.season_number);
    Golbal.get_cache_or_ajax("get_season_episodes", "season" + seasons.season_number,
        {tmdbid: this.tmdbid, season: seasons.season_number, title: this.title, year: this.year}, (ret) => {
      //console.log(ret);
      if (ret.code === 0 && ret.episodes?.length !== 0) {
        seasons.is_loadok = true;
        seasons.list = ret.episodes;
      } else {
        seasons.is_loading = false;
        seasons.is_loaderror = true;
      }
      this.requestUpdate();
    });
  }

  render() {
    return html`
      <div class="accordion m-2" id="lit-accordion-seasons">
        ${this.seasons_data.map((seasons, seasons_index) => (
          html`
            <div class="accordion-item">
              <div class="accordion-header" id="lit-accordion-seasons-heading-${seasons_index}">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#lit-accordion-seasons-collapse-${seasons_index}" aria-expanded="false"
                  @click=${() => {
                    if (!seasons.is_loadok && !seasons.is_loading && !seasons.is_loaderror) {
                      seasons.is_loading = true;
                      this._get_episodes_list(seasons);
                    }
                  }}>
                  <h2 class="mt-2">第 ${seasons.season_number} 季</h2>
                  ${seasons.air_date ? html`<h3 class="ms-2 mt-2"> - ${seasons.air_date.split("-")[0]}</h3>` : nothing}
                  <div class="d-flex flex-grow-1 justify-content-between">
                    ${seasons.episode_count ? html`<div><strong class="badge badge-pill mx-3">共${seasons.episode_count}集</strong></div>` : nothing}
                    ${seasons.state ? html`<div><strong class="badge badge-pill bg-green text-white mx-3">已入库</strong></div>`: nothing}
                  </div>
                </button>
              </div>
              <div id="lit-accordion-seasons-collapse-${seasons_index}" class="accordion-collapse collapse" data-bs-parent="#lit-accordion-seasons">
                <div class="accordion-body">
                ${seasons.list
                ? seasons.list.map((episodes, episodes_index) => (
                  html`
                    <div class="row pt-3 pb-3 custom-border-top">
                      <div class="col-lg-8">
                        <h3>
                          ${seasons.list.length - episodes_index} - ${episodes.name}
                          ${episodes.air_date ? html`<span class="badge badge-pill ms-1 p-1 px-2">
                            <small>${episodes.air_date}</small></span>` : nothing}
                          ${episodes.state ? html`<span class="badge badge-pill bg-green ms-1 p-1">
                            <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-check" width="24" height="24"
                                 viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
                                 stroke-linejoin="round">
                              <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                              <path d="M5 12l5 5l10 -10"></path>
                            </svg>
                          </span>` : nothing}
                        </h3>
                        ${episodes.overview ? html`<h3 class="text-muted">${episodes.overview}</h3>` : nothing}
                      </div>
                      <div class="col-lg-4 align-self-center">
                        ${episodes.still_path ? html`
                          <custom-img style="height: auto;"
                              img-class="rounded-3 object-cover"
                              img-ratio="50%"
                              img-src="${episodes.still_path}"
                          ></custom-img>` : nothing}
                      </div>  
                    </div>
                  ` ))
                : seasons.is_loaderror
                ? html`
                      <button class="btn btn-pill"
                        @click=${ () => {
                          seasons.is_loading = true;
                          seasons.is_loaderror = false;
                          this.requestUpdate();
                          Golbal.del_page_data("get_season_episodes", "season" + seasons.season_number);
                          this._get_episodes_list(seasons);
                        }}
                      >重新加载</button>
                  `
                : Array(seasons.episode_count ?? 10).fill(
                  html`
                    <div class="accordion-body placeholder-glow">
                      <div class="placeholder col-12"></div>
                    </div>
                  `)
                }
                </div>  
              </div>
            </div>
          `
        ))}
      </div>
    `;
  }

}

window.customElements.define("accordion-seasons", AccordionSeasons);